import asyncio
import copy
import logging
from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bp_client import BackpackTFClient, BackpackTFError
from app.core.scanner import BuyorderError, Scanner
from app.core.sync_tracker import SyncTracker
from app.crud import get_stored_listings, save_buyorder_state_history
from app.db import models
from app.models.enums import Intent
from app.models.listings import (
    CurrencyValue,
    SnapshotBPListing,
)
from app.services.listing_service import sync_listings

logger = logging.getLogger(__name__)


async def sync_and_scan_orders(
    db: AsyncSession,
    bp: BackpackTFClient,
    scanner: Scanner,
    tracker: SyncTracker,
    intent: Intent,
):
    listings = await sync_listings(db, bp, sync_all=True)
    logger.info("Synced %d listings", len(listings))
    await refresh_order_states(db, scanner, tracker, intent)


async def refresh_order_states(
    db: AsyncSession, scanner: Scanner, tracker: SyncTracker, intent: Intent
) -> None:
    listings = await get_stored_listings(db, intent=intent)
    tracker.total = len(listings)
    tracker.update_progress(0, len(listings))
    counts: dict[str, int] = {"new": 0, "updated": 0, "unchanged": 0, "skipped": 0}
    for i, listing in enumerate(listings):
        _, status = await update_order_data(db, scanner, listing)
        counts[status] += 1
        tracker.update_progress(i + 1, len(listings))
        await asyncio.sleep(1)  # for rate limiter
    logger.info(
        "Scanned %d orders: %d new, %d updated, %d unchanged, %d skipped",
        len(listings),
        counts["new"],
        counts["updated"],
        counts["unchanged"],
        counts["skipped"],
    )


async def update_order_data(
    db: AsyncSession, scanner: Scanner, order: models.Listing
) -> tuple[models.SellorderState | models.BuyorderState | None, str]:
    try:
        item_listings = await scanner.fetch_item_listings(order.item.name)
    except BackpackTFError as e:
        logger.warning("Failed to fetch snapshot for %s: %s", order.item.name, e)
        return None, "skipped"
    buyorders = [listing for listing in item_listings if listing.intent == "buy"]
    sellorders = [listing for listing in item_listings if listing.intent == "sell"]
    try:
        if order.intent == Intent.buy:
            users_price = scanner.resolve_users_price(buyorders)
        else:
            users_price = scanner.resolve_users_price(sellorders)
    except BuyorderError as e:
        logger.warning(
            "No %sorder found for %s, skipping. Error: %s",
            order.intent,
            order.item.name,
            e,
        )
        order.status = "inactive"
        await db.commit()
        return None, "skipped"
    if order.intent == Intent.buy:
        top_competitor_buyorder = scanner.get_highest_competitor_buyorder(buyorders)
        lowest_sellorder = scanner.get_lowest_sellorder(sellorders)
        lowest_currency = lowest_sellorder.currencies if lowest_sellorder else None
        buyorder_state, status = await _update_order_state(
            db,
            order,
            users_price,
            top_competitor_buyorder,
            lowest_currency,
            models.BuyorderState,
            _apply_buyorder_values,
        )
        return buyorder_state, status
    else:
        highest_buyorder = scanner.get_highest_buyorder(buyorders)
        lowest_competitor_sellorder = scanner.get_lowest_competitor_sellorder(
            sellorders
        )
        highest_currency = highest_buyorder.currencies if highest_buyorder else None
        sellorder_state, status = await _update_order_state(
            db,
            order,
            users_price,
            lowest_competitor_sellorder,
            highest_currency,
            models.SellorderState,
            _apply_sellorder_values,
        )
        return sellorder_state, status


async def _update_order_state(
    db: AsyncSession,
    listing: models.Listing,
    users_price: CurrencyValue,
    competitor_order: SnapshotBPListing | None,
    opposing_price: CurrencyValue | None,
    state_type: type,
    # apply_values_fn is a callback: _apply_buyorder_values or _apply_sellorder_values
    apply_values_fn: Callable,
) -> tuple[models.SellorderState, str] | tuple[models.BuyorderState, str]:
    old_order_state = await db.get(state_type, listing.id)

    if old_order_state:
        old_copy = copy.deepcopy(
            old_order_state
        )  # preserve old order state before merge
        apply_values_fn(
            old_order_state,
            users_price,
            competitor_order,
            opposing_price,
        )
        if old_copy.is_same_as(old_order_state):
            logger.debug("No change in order state for item v%s", listing.item.name)
            return old_order_state, "unchanged"
        await db.commit()
        if listing.intent == Intent.buy:
            await save_buyorder_state_history(db, old_copy, old_order_state)
        # await save_order_state_history(db, old_copy, old_sellorder_state)
        logger.debug(
            "Updated order state for %sorder for item %s",
            listing.intent,
            listing.item.name,
        )
        return old_order_state, "updated"

    order_state = state_type(
        listing_id=listing.id,
        steamid=listing.steamid,
        item_name=listing.item.name,
    )
    apply_values_fn(
        order_state,
        users_price,
        competitor_order,
        opposing_price,
    )
    db.add(order_state)
    await db.commit()
    logger.debug("New %sorder state for item %s", listing.intent, listing.item.name)
    return order_state, "new"


def _apply_buyorder_values(
    state: models.BuyorderState,
    users_price: CurrencyValue,
    top_competitor_buyorder: SnapshotBPListing | None,
    lowest_seller_currency: CurrencyValue | None,
):
    state.user_keys = int(users_price.keys) if users_price.keys else 0
    state.user_metal = users_price.metal
    if top_competitor_buyorder:
        state.is_outbid = users_price < top_competitor_buyorder.currencies
        state.top_competitor_keys = (
            int(top_competitor_buyorder.currencies.keys)
            if top_competitor_buyorder.currencies.keys is not None
            else 0
        )
        state.top_competitor_metal = top_competitor_buyorder.currencies.metal
        state.outbid_by = top_competitor_buyorder.steamid
    if lowest_seller_currency:
        state.lowest_seller_keys = (
            int(lowest_seller_currency.keys) if lowest_seller_currency.keys else 0
        )
        state.lowest_seller_metal = lowest_seller_currency.metal


def _apply_sellorder_values(
    state: models.SellorderState,
    users_price: CurrencyValue,
    lowest_competitor_buyorder: SnapshotBPListing | None,
    highest_seller_currency: CurrencyValue | None,
):
    state.user_keys = int(users_price.keys) if users_price.keys else 0
    state.user_metal = users_price.metal
    if lowest_competitor_buyorder:
        state.is_undercut = users_price > lowest_competitor_buyorder.currencies
        state.lowest_competitor_keys = (
            int(lowest_competitor_buyorder.currencies.keys)
            if lowest_competitor_buyorder.currencies.keys is not None
            else None
        )
        state.lowest_competitor_metal = lowest_competitor_buyorder.currencies.metal
        state.undercut_by = lowest_competitor_buyorder.steamid
    if highest_seller_currency:
        state.highest_buyer_keys = (
            int(highest_seller_currency.keys)
            if highest_seller_currency.keys is not None
            else None
        )
        state.highest_buyer_metal = highest_seller_currency.metal
