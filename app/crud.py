from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
import logging
from app.models.listings import ItemData, BPListing
from app.db import models

logger = logging.getLogger(__name__)


async def get_stored_listings(
    db: AsyncSession, intent: str | None = None
) -> list[models.Listing]:
    stmt = select(models.Listing).options(joinedload(models.Listing.item))
    if intent:
        stmt = stmt.where(models.Listing.intent == intent)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_stored_buyorder_states(
    db: AsyncSession, only_beaten: bool = False
) -> list[models.BuyorderState]:
    stmt = select(models.BuyorderState).options(
        joinedload(models.BuyorderState.listing).joinedload(models.Listing.item)
    )
    if only_beaten:
        stmt = stmt.where(models.BuyorderState.is_outbid == only_beaten)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_stored_buyorder_state_histories(
    db: AsyncSession,
) -> list[models.BuyorderStateHistory]:
    stmt = (
        select(models.BuyorderStateHistory)
        .options(
            joinedload(models.BuyorderStateHistory.listing).joinedload(
                models.Listing.item
            )
        )
        .order_by(models.BuyorderStateHistory.changed_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def save_buyorder_state_history(
    db: AsyncSession,
    old_buyorder_state: models.BuyorderState,
    new_buyorder_state: models.BuyorderState,
):
    buyorder_state_history = models.BuyorderStateHistory(
        listing_id=new_buyorder_state.listing_id,
        old_user_keys=old_buyorder_state.user_keys,
        old_user_metal=old_buyorder_state.user_metal,
        old_top_competitor_keys=old_buyorder_state.top_competitor_keys,
        old_top_competitor_metal=old_buyorder_state.top_competitor_metal,
        old_is_outbid=old_buyorder_state.is_outbid,
        old_lowest_seller_keys=old_buyorder_state.lowest_seller_keys,
        old_lowest_seller_metal=old_buyorder_state.lowest_seller_metal,
        new_user_keys=new_buyorder_state.user_keys,
        new_user_metal=new_buyorder_state.user_metal,
        new_top_competitor_keys=new_buyorder_state.top_competitor_keys,
        new_top_competitor_metal=new_buyorder_state.top_competitor_metal,
        new_is_outbid=new_buyorder_state.is_outbid,
        new_lowest_seller_keys=new_buyorder_state.lowest_seller_keys,
        new_lowest_seller_metal=new_buyorder_state.lowest_seller_metal,
        # change types
        outbid_changed=old_buyorder_state.is_outbid != new_buyorder_state.is_outbid,
    )
    if (old_buyorder_state.is_outbid) and (not new_buyorder_state.is_outbid):
        buyorder_state_history.regained_top_changed = True
    if (
        old_buyorder_state.top_competitor_keys != new_buyorder_state.top_competitor_keys
    ) or (
        old_buyorder_state.top_competitor_metal
        != new_buyorder_state.top_competitor_metal
    ):
        buyorder_state_history.competitor_price_changed = True
    if (old_buyorder_state.user_keys != new_buyorder_state.user_keys) or (
        old_buyorder_state.user_metal != new_buyorder_state.user_metal
    ):
        buyorder_state_history.price_updated_changed = True

    if (
        old_buyorder_state.lowest_seller_keys != new_buyorder_state.lowest_seller_keys
    ) or (
        old_buyorder_state.lowest_seller_metal != new_buyorder_state.lowest_seller_metal
    ):
        buyorder_state_history.lowest_seller_changed = True
    db.add(buyorder_state_history)


async def get_listing(
    db: AsyncSession, id: str, status: str = "active"
) -> models.Listing | None:
    stmt = (
        select(models.Listing)
        .options(joinedload(models.Listing.item))
        .where(models.Listing.id == id, models.Listing.status == status)
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_or_create_item(db: AsyncSession, item_data: ItemData) -> models.Item:
    result = await db.execute(
        select(models.Item).where(
            models.Item.defindex == item_data.defindex,
            models.Item.name == item_data.name,
            models.Item.quality == item_data.quality,
            models.Item.particle == item_data.particle,
        )
    )

    item = result.scalar_one_or_none()

    if not item:
        item = models.Item(
            defindex=item_data.defindex,
            name=item_data.name,
            quality=item_data.quality,
            particle=item_data.particle,
        )
        db.add(item)
        logger.info("Item created: %s", item_data.name)
        await db.flush()  # gets item.id without committing
    return item


async def upsert_listing(
    db: AsyncSession, listing: BPListing, item_id: int
) -> models.Listing:
    existing = await db.get(models.Listing, listing.id)
    if existing:
        if (
            existing.keys != listing.currencies.keys
            or existing.metal != listing.currencies.metal
        ):
            existing.keys = (
                int(listing.currencies.keys) if listing.currencies.keys else 0
            )
            existing.metal = listing.currencies.metal
            existing.status = listing.status
            logger.info("Currency updated for listing for item: %s", listing.item.name)
        return existing

    new_listing = models.Listing(
        id=listing.id,
        steamid=listing.steamid,
        intent=listing.intent,
        status=listing.status,
        keys=listing.currencies.keys,
        metal=listing.currencies.metal,
        item_id=item_id,
        item_url=listing.item_url,
    )
    db.add(new_listing)
    logger.info("listing created for item: %s", listing.item.name)
    return new_listing
