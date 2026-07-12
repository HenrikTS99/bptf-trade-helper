import asyncio
import logging
import copy

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.sync_tracker import SyncTracker
from app.core.bp_client import BackpackTFError, BackpackTFClient
from app.core.scanner import BuyorderError, Scanner
from app.crud import get_stored_listings, save_buyorder_state_history
from app.db import models
from app.models.listings import (
    CurrencyValue,
    SnapshotBPListing,
)
from app.services.listing_service import sync_listings

logger = logging.getLogger(__name__)


async def refresh_buyorder_states(
    db: AsyncSession, scanner: Scanner, tracker: SyncTracker
) -> None:
    listings = await get_stored_listings(db, intent="buy")
    tracker.total = len(listings)
    tracker.update_progress(0, len(listings))
    counts: dict[str, int] = {"new": 0, "updated": 0, "unchanged": 0, "skipped": 0}
    for i, listing in enumerate(listings):
        _, status = await update_buyorder_data(db, scanner, listing)
        counts[status] += 1
        tracker.update_progress(i + 1, len(listings))
        await asyncio.sleep(1)  # for rate limiter
    logger.info(
        "Scanned %d buyorders: %d new, %d updated, %d unchanged, %d skipped",
        len(listings),
        counts["new"],
        counts["updated"],
        counts["unchanged"],
        counts["skipped"],
    )


async def update_buyorder_data(
    db: AsyncSession, scanner: Scanner, order: models.Listing
) -> tuple[models.BuyorderState | None, str]:
    try:
        item_listings = await scanner.fetch_item_listings(order.item.name)
    except BackpackTFError as e:
        logger.warning("Failed to fetch snapshot for %s: %s", order.item.name, e)
        return None, "skipped"
    buyorders = [listing for listing in item_listings if listing.intent == "buy"]
    sellorders = [listing for listing in item_listings if listing.intent == "sell"]
    try:
        users_price = scanner.resolve_users_price(buyorders)
    except BuyorderError as e:
        logger.warning(
            "No buyorder found for %s, skipping. Error: %s", order.item.name, e
        )
        order.status = "inactive"
        await db.commit()
        return None, "skipped"
    top_competitor_buyorder = scanner.get_highest_competitor_buyorder(buyorders)
    lowest_sellorder = scanner.get_lowest_sellorder(sellorders)
    lowest_currency = lowest_sellorder.currencies if lowest_sellorder else None
    buyorder_state, status = await _update_buyorder_state(
        db, order, users_price, top_competitor_buyorder, lowest_currency
    )
    return buyorder_state, status


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
            if top_competitor_buyorder.currencies.keys
            else 0
        )
        state.top_competitor_metal = top_competitor_buyorder.currencies.metal
        state.outbid_by = top_competitor_buyorder.steamid
    if lowest_seller_currency:
        state.lowest_seller_keys = (
            int(lowest_seller_currency.keys) if lowest_seller_currency.keys else 0
        )
        state.lowest_seller_metal = lowest_seller_currency.metal


async def _update_buyorder_state(
    db: AsyncSession,
    listing: models.Listing,
    users_price: CurrencyValue,
    top_competitor_buyorder: SnapshotBPListing | None,
    lowest_seller_currency: CurrencyValue | None,
) -> tuple[models.BuyorderState, str]:
    old_buyorder_state = await db.get(models.BuyorderState, listing.id)

    if old_buyorder_state:
        old_copy = copy.deepcopy(
            old_buyorder_state
        )  # preserve old buyorderState before merge
        _apply_buyorder_values(
            old_buyorder_state,
            users_price,
            top_competitor_buyorder,
            lowest_seller_currency,
        )
        if old_copy.is_same_as(old_buyorder_state):
            logger.debug("No change in buyorder state for item v%s", listing.item.name)
            return old_buyorder_state, "unchanged"
        await db.commit()
        await save_buyorder_state_history(db, old_copy, old_buyorder_state)
        logger.debug(
            "Updated buyorder state for buyorder for item %s", listing.item.name
        )
        return old_buyorder_state, "updated"

    buyorder_state = models.BuyorderState(
        listing_id=listing.id,
        steamid=listing.steamid,
        item_name=listing.item.name,
    )
    _apply_buyorder_values(
        buyorder_state,
        users_price,
        top_competitor_buyorder,
        lowest_seller_currency,
    )
    db.add(buyorder_state)
    await db.commit()
    logger.debug("New buyorder state for item %s", listing.item.name)
    return buyorder_state, "new"


async def sync_and_scan(
    db: AsyncSession, bp: BackpackTFClient, scanner: Scanner, tracker: SyncTracker
):
    listings = await sync_listings(db, bp, sync_all=True)
    logger.info("Synced %d listings", len(listings))
    await refresh_buyorder_states(db, scanner, tracker)
