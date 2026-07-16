import asyncio
import copy
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bp_client import BackpackTFClient, BackpackTFError
from app.core.scanner import BuyorderError, Scanner
from app.core.sync_tracker import SyncTracker
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


async def sync_and_scan_buyorders(
    db: AsyncSession, bp: BackpackTFClient, scanner: Scanner, tracker: SyncTracker
):
    listings = await sync_listings(db, bp, sync_all=True)
    logger.info("Synced %d listings", len(listings))
    await refresh_buyorder_states(db, scanner, tracker)


async def refresh_sellorder_states(
    db: AsyncSession, scanner: Scanner, tracker: SyncTracker
) -> None:
    listings = await get_stored_listings(db, intent="sell")
    tracker.total = len(listings)
    tracker.update_progress(0, len(listings))
    counts: dict[str, int] = {"new": 0, "updated": 0, "unchanged": 0, "skipped": 0}
    for i, listing in enumerate(listings):
        _, status = await update_sellorder_data(db, scanner, listing)
        counts[status] += 1
        tracker.update_progress(i + 1, len(listings))
        await asyncio.sleep(1)  # for rate limiter
    logger.info(
        "Scanned %d sellorder: %d new, %d updated, %d unchanged, %d skipped",
        len(listings),
        counts["new"],
        counts["updated"],
        counts["unchanged"],
        counts["skipped"],
    )


async def update_sellorder_data(
    db: AsyncSession, scanner: Scanner, order: models.Listing
) -> tuple[models.SellorderState | None, str]:
    try:
        item_listings = await scanner.fetch_item_listings(order.item.name)
    except BackpackTFError as e:
        logger.warning("Failed to fetch snapshot for %s: %s", order.item.name, e)
        return None, "skipped"
    buyorders = [listing for listing in item_listings if listing.intent == "buy"]
    sellorders = [listing for listing in item_listings if listing.intent == "sell"]
    try:
        users_price = scanner.resolve_users_price(sellorders)
    except BuyorderError as e:
        logger.warning(
            "No sellorder found for %s, skipping. Error: %s", order.item.name, e
        )
        order.status = "inactive"
        await db.commit()
        return None, "skipped"
    highest_buyorder = scanner.get_highest_buyorder(buyorders)
    lowest_competitor_sellorder = scanner.get_lowest_competitor_sellorder(sellorders)
    highest_currency = highest_buyorder.currencies if highest_buyorder else None
    sellorder_state, status = await _update_sellorder_state(
        db, order, users_price, lowest_competitor_sellorder, highest_currency
    )
    return sellorder_state, status


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


async def _update_sellorder_state(
    db: AsyncSession,
    listing: models.Listing,
    users_price: CurrencyValue,
    lowest_competitor_sellorder: SnapshotBPListing | None,
    highest_seller_currency: CurrencyValue | None,
) -> tuple[models.SellorderState, str]:
    old_sellorder_state = await db.get(models.SellorderState, listing.id)

    if old_sellorder_state:
        old_copy = copy.deepcopy(
            old_sellorder_state
        )  # preserve old sellorderState before merge
        _apply_sellorder_values(
            old_sellorder_state,
            users_price,
            lowest_competitor_sellorder,
            highest_seller_currency,
        )
        if old_copy.is_same_as(old_sellorder_state):
            logger.debug("No change in sellorder state for item v%s", listing.item.name)
            return old_sellorder_state, "unchanged"
        await db.commit()
        # await save_sellorder_state_history(db, old_copy, old_sellorder_state)
        logger.debug(
            "Updated sellorder state for sellorder for item %s", listing.item.name
        )
        return old_sellorder_state, "updated"

    sellorder_state = models.SellorderState(
        listing_id=listing.id,
        steamid=listing.steamid,
        item_name=listing.item.name,
    )
    _apply_sellorder_values(
        sellorder_state,
        users_price,
        lowest_competitor_sellorder,
        highest_seller_currency,
    )
    db.add(sellorder_state)
    await db.commit()
    logger.debug("New sellorder state for item %s", listing.item.name)
    return sellorder_state, "new"


async def sync_and_scan_sellorders(
    db: AsyncSession, bp: BackpackTFClient, scanner: Scanner, tracker: SyncTracker
):
    listings = await sync_listings(db, bp, sync_all=True)
    logger.info("Synced %d listings", len(listings))
    await refresh_sellorder_states(db, scanner, tracker)
