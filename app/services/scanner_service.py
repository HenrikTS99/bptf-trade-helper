import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.bp_client import BackpackTFError
from app.core.scanner import BuyorderError, Scanner
from app.crud import get_stored_listings
from app.db import models
from app.models.listings import (
    CurrencyValue,
    SnapshotBPListing,
)

logger = logging.getLogger(__name__)


async def refresh_buyorder_states(db: AsyncSession, scanner: Scanner) -> None:
    listings = await get_stored_listings(db, intent="buy")
    counts: dict[str, int] = {"new": 0, "updated": 0, "unchanged": 0, "skipped": 0}
    for listing in listings:
        status = await _update_buyorder_data(db, scanner, listing)
        counts[status] += 1
        await asyncio.sleep(1)  # for rate limiter
    logger.info(
        "Scanned %d buyorders: %d new, %d updated, %d unchanged, %d skipped",
        len(listings),
        counts["new"],
        counts["updated"],
        counts["unchanged"],
        counts["skipped"],
    )


async def _update_buyorder_data(
    db: AsyncSession, scanner: Scanner, order: models.Listing
) -> str:
    try:
        buyorders = await scanner._fetch_item_buyorders(order.item.name)
    except BackpackTFError as e:
        logger.warning("Failed to fetch snapshot for %s: %s", order.item.name, e)
        return "skipped"
    try:
        users_price = scanner._resolve_users_price(buyorders)
    except BuyorderError as e:
        logger.warning(
            "No buyorder found for %s, skipping. Error: %s", order.item.name, e
        )
        return "skipped"
    top_competitor_buyorder = scanner._get_highest_competitor_buyorder(buyorders)
    _, status = await _update_buyorder_state(
        db, order, users_price, top_competitor_buyorder
    )
    return status


async def _update_buyorder_state(
    db: AsyncSession,
    listing: models.Listing,
    users_price: CurrencyValue,
    top_competitor_buyorder: SnapshotBPListing | None,
) -> tuple[models.BuyorderState, str]:
    old_buyorder_state = await db.get(models.BuyorderState, listing.id)
    outbid = False

    if top_competitor_buyorder:
        outbid = users_price < top_competitor_buyorder.currencies
    buyorder_state = models.BuyorderState(
        listing_id=listing.id,
        steamid=listing.steamid,
        item_name=listing.item.name,
        user_keys=users_price.keys,
        user_metal=users_price.metal,
    )
    if top_competitor_buyorder:
        buyorder_state.top_competitor_keys = top_competitor_buyorder.currencies.keys
        buyorder_state.top_competitor_metal = top_competitor_buyorder.currencies.metal

        buyorder_state.outbid_by = top_competitor_buyorder.steamid
        buyorder_state.is_outbid = outbid

    if old_buyorder_state:
        if _is_same_buyorder_state(old_buyorder_state, buyorder_state):
            logger.debug("No change in buyorder state for item %s", listing.item.name)
            return old_buyorder_state, "unchanged"
    buyorder_state = await db.merge(buyorder_state)
    await db.commit()
    if old_buyorder_state:
        logger.debug(
            "Updated buyorder state for buyorder for item %s", listing.item.name
        )
        return buyorder_state, "updated"
    logger.debug("New buyorder state for item %s", listing.item.name)
    return buyorder_state, "new"


def _is_same_buyorder_state(
    old_buyorder_state: models.BuyorderState, buyorder_state: models.BuyorderState
):
    return (
        old_buyorder_state.user_keys == buyorder_state.user_keys
        and old_buyorder_state.user_metal == buyorder_state.user_metal
        and old_buyorder_state.top_competitor_keys == buyorder_state.top_competitor_keys
        and old_buyorder_state.top_competitor_metal
        == buyorder_state.top_competitor_metal
        and old_buyorder_state.is_outbid == buyorder_state.is_outbid
        and old_buyorder_state.outbid_by == buyorder_state.outbid_by
    )
