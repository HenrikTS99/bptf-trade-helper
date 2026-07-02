import logging
import math
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.enums import RoundingMethod
from app.core.bp_client import BackpackTFClient
from app.db import models
from app.models.listings import BPListing, ItemData, CurrencyValue

logger = logging.getLogger(__name__)


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


async def _upsert_listing(
    db: AsyncSession, listing: BPListing, item_id: int
) -> models.Listing | None:
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


async def update_listing_price(
    db: AsyncSession,
    listing: models.Listing,
    rounding_strategy: str,
    bp: BackpackTFClient,
) -> models.Listing | None:
    highest_buyorder_value = await get_top_competitor_price(db, listing.id)
    if not highest_buyorder_value:
        return None

    keys = int(highest_buyorder_value.keys or 0)
    # TODO: very important to not have mistakes here, make tests for this.
    if rounding_strategy == RoundingMethod.UP_1_KEY:
        keys += 1
    elif rounding_strategy == RoundingMethod.NEAREST_5_KEY:
        keys = math.ceil((keys + 1) / 5) * 5
    elif rounding_strategy == RoundingMethod.NEAREST_10_KEY:
        keys = math.ceil((keys + 1) / 10) * 10

    res_listing = await bp.patch_listing_price(listing.id, keys=keys, metal=0)

    item = await _get_or_create_item(db, res_listing.item)
    # Update and get the listing
    updated_listing = await _upsert_listing(db, res_listing, item.id)
    await db.commit()
    await db.refresh(updated_listing)
    return updated_listing


async def get_top_competitor_price(
    db: AsyncSession, listing_id: str
) -> CurrencyValue | None:
    buyorder_state = await db.get(models.BuyorderState, listing_id)
    if not buyorder_state:
        return None
    return CurrencyValue(
        keys=buyorder_state.top_competitor_keys,
        metal=buyorder_state.top_competitor_metal,
    )


async def update_buyorder_price(
    db: AsyncSession, listing: models.Listing
) -> models.BuyorderState | None:
    buyorder_state = await db.get(models.BuyorderState, listing.id)
    if not buyorder_state:
        return

    buyorder_state.user_keys = listing.keys
    buyorder_state.user_metal = listing.metal
    if CurrencyValue(
        keys=buyorder_state.user_keys, metal=buyorder_state.user_metal
    ) >= CurrencyValue(
        keys=buyorder_state.top_competitor_keys,
        metal=buyorder_state.top_competitor_metal,
    ):
        buyorder_state.is_outbid = False
        buyorder_state.outbid_by = None

    buyorder_state = await db.merge(buyorder_state)
    await db.commit()
    logger.debug("Updated buyorder state for buyorder for item %s", listing.item.name)
    return buyorder_state
