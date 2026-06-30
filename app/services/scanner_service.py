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
    for listing in listings:
        await _update_buyorder_data(db, scanner, listing)
        await asyncio.sleep(1)  # for rate limiter


async def _update_buyorder_data(
    db: AsyncSession, scanner: Scanner, order: models.Listing
):
    try:
        buyorders = await scanner._fetch_item_buyorders(order.item.name)
    except BackpackTFError as e:
        logger.warning("Failed to fetch snapshot for %s: %s", order.item.name, e)
        return
    try:
        users_price = scanner._resolve_users_price(buyorders)
    except BuyorderError as e:
        logger.warning(
            "No buyorder found for %s, skipping. Error: %s", order.item.name, e
        )
        return
    top_competitor_buyorder = scanner._get_highest_competitor_buyorder(buyorders)
    await _update_buyorder_state(db, order, users_price, top_competitor_buyorder)


async def _update_buyorder_state(
    db: AsyncSession,
    listing: models.Listing,
    users_price: CurrencyValue,
    top_competitor_buyorder: SnapshotBPListing | None,
) -> models.BuyorderState:
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
    db.add(buyorder_state)
    await db.commit()
    logger.info("Updated buyorder state for buyorder for item %s", listing.item.name)
    return buyorder_state
