import asyncio
import logging

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


async def _update_buyorder_state(
    db: AsyncSession,
    listing: models.Listing,
    users_price: CurrencyValue,
    top_competitor_buyorder: SnapshotBPListing | None,
    lowest_seller_currency: CurrencyValue | None,
) -> tuple[models.BuyorderState, str]:
    old_buyorder_state = await db.get(models.BuyorderState, listing.id)

    buyorder_state = models.BuyorderState(
        listing_id=listing.id,
        steamid=listing.steamid,
        item_name=listing.item.name,
        user_keys=users_price.keys,
        user_metal=users_price.metal,
    )
    if top_competitor_buyorder:
        buyorder_state.is_outbid = users_price < top_competitor_buyorder.currencies
        buyorder_state.top_competitor_keys = (
            int(top_competitor_buyorder.currencies.keys)
            if top_competitor_buyorder.currencies.keys
            else 0
        )
        buyorder_state.top_competitor_metal = top_competitor_buyorder.currencies.metal

        buyorder_state.outbid_by = top_competitor_buyorder.steamid

    if lowest_seller_currency:
        buyorder_state.lowest_seller_keys = (
            int(lowest_seller_currency.keys) if lowest_seller_currency.keys else 0
        )
        buyorder_state.lowest_seller_metal = lowest_seller_currency.metal

    if old_buyorder_state and old_buyorder_state.is_same_as(buyorder_state):
        logger.debug("No change in buyorder state for item %s", listing.item.name)
        return old_buyorder_state, "unchanged"

    buyorder_state = await db.merge(buyorder_state)
    await db.commit()
    if old_buyorder_state:
        logger.debug(
            "Updated buyorder state for buyorder for item %s", listing.item.name
        )
        await save_buyorder_state_history(db, old_buyorder_state, buyorder_state)
        return buyorder_state, "updated"
    logger.debug("New buyorder state for item %s", listing.item.name)
    return buyorder_state, "new"


async def sync_and_scan(
    db: AsyncSession, bp: BackpackTFClient, scanner: Scanner, tracker: SyncTracker
):
    listings = await sync_listings(db, bp, sync_all=True)
    logger.info("Synced %d listings", len(listings))
    await refresh_buyorder_states(db, scanner, tracker)
