import logging
from app.models.listings import (
    BPListing,
    CurrencyValue,
    SnapshotBPListing,
)
import asyncio
from app.core.scanner import Scanner, BuyorderError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.listing_service import get_stored_listings
from app.core.bp_client import BackpackTFError
from app.db import models

from app.models.listings import BPListing

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
    # outbidder = self._find_outbidding_order(buyorders, users_price)
    # buyorder_data = self._build_buyorder_data(
    #     order.item.name, users_price, top_competitor_buyorder
    # )
    await _update_buyorder_state(db, order, users_price, top_competitor_buyorder)
    # await _upsert_buyorder_state(db, buyorder_state)


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


# async def _upsert_buyorder_state(db, buyorder_state):
#     result = await db.execute(
#         select(models.BuyorderState).where(models.BuyorderState.id == buyorder_state.id)
#     )
#     # Give first column of first row, no rows returns None
#     existing = result.scalar_one_or_none()
#
#     if existing:
#         existing.user_keys = buyorder_state.user_keys
#         existing.user_metal = buyorder_state.user_metal
#         existing.top_competitor_keys = buyorder_state.top_competitor_keys
#         existing.top_competitor_metal = buyorder_state.top_competitor_metal
#         existing.outbid_by = buyorder_state.outbid_by
#         existing.is_outbid = buyorder_state.is_outbid
#         return
