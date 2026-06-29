from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app.db import models
from app.core.bp_client import BackpackTFClient
from app.models.listings import BPListing, ItemData
import logging

logger = logging.getLogger(__name__)


async def get_stored_listings(
    db: AsyncSession, intent: str | None = None
) -> list[models.Listing]:
    stmt = select(models.Listing).options(joinedload(models.Listing.item))
    if intent:
        stmt = stmt.where(models.Listing.intent == intent)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_stored_buyorder_states(
    db: AsyncSession, only_beaten: bool = False
) -> list[models.BuyorderState]:
    stmt = select(models.BuyorderState).options(
        joinedload(models.BuyorderState.listing)
    )
    if only_beaten == True:
        stmt = stmt.where(models.BuyorderState.is_outbid == only_beaten)
    result = await db.execute(stmt)
    return result.scalars().all()


async def sync_listings(
    db: AsyncSession,
    bp: BackpackTFClient,
    intent: str | None = None,
    limit: int = 1000,
    sync_all=False,
) -> list[BPListing]:
    skip = 0
    all_listings = []
    first_page_only = not sync_all
    try:
        while True:
            listings, cursor = await bp.get_listings(
                intent=intent, limit=limit, skip=skip
            )
            for listing in listings:
                # Find or create the item
                item = await _get_or_create_item(db, listing.item)
                # Find or create the listing
                await _upsert_listing(db, listing, item.id)

            all_listings.extend(listings)

            if first_page_only or not cursor:
                break
            total = cursor.get("total", 0)
            skip += limit
            if skip >= total and len(listings) < limit:
                break
        await db.commit()
        logger.info("Synced %d listings", len(all_listings))
    except Exception:
        await db.rollback()
        raise
    return all_listings


async def _get_or_create_item(db: AsyncSession, item_data: ItemData) -> models.Item:
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


async def _upsert_listing(db: AsyncSession, listing: BPListing, item_id: int) -> None:
    result = await db.execute(
        select(models.Listing).where(models.Listing.id == listing.id)
    )
    # Give first column of first row, no rows returns None
    existing = result.scalar_one_or_none()

    if existing:
        if (
            existing.keys != listing.currencies.keys
            or existing.metal != listing.currencies.metal
        ):
            existing.keys = listing.currencies.keys
            existing.metal = listing.currencies.metal
            existing.status = listing.status
            logger.info("Currency updated for listing for item: %s", listing.item.name)
        return

    db.add(
        models.Listing(
            id=listing.id,
            steamid=listing.steamid,
            intent=listing.intent,
            status=listing.status,
            keys=listing.currencies.keys,
            metal=listing.currencies.metal,
            item_id=item_id,
            item_url=listing.item_url,
        )
    )
    logger.info("listing created for item: %s", listing.item.name)
