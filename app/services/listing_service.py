import copy
import logging
import math

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bp_client import BackpackTFClient
from app.crud import get_or_create_item, save_buyorder_state_history, upsert_listing
from app.db import models
from app.models.enums import Intent, RoundingMethod
from app.models.listings import BPListing, CurrencyValue

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
                item = await get_or_create_item(db, listing.item)
                # Find or create the listing
                await upsert_listing(db, listing, item.id)

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


async def update_listing_price(
    db: AsyncSession,
    listing: models.Listing,
    rounding_strategy: RoundingMethod,
    bp: BackpackTFClient,
) -> models.Listing | None:
    competitor_price = await get_competitor_price(db, listing.id, listing.intent)
    if not competitor_price:
        return None

    new_listing_price = apply_rounding_strategy(
        int(competitor_price.keys or 0),
        competitor_price.metal or 0,
        rounding_strategy,
        competitor_price.metal,
    )
    if new_listing_price is None:
        return None
    res_listing = await bp.patch_listing_price(
        listing.id, keys=new_listing_price.keys, metal=new_listing_price.metal
    )

    item = await get_or_create_item(db, res_listing.item)
    # Update and get the listing
    updated_listing = await upsert_listing(db, res_listing, item.id)
    await db.commit()
    await db.refresh(updated_listing)
    return updated_listing


def apply_rounding_strategy(
    keys: int, metal: float, strategy: RoundingMethod, competitor_metal: float | None
) -> CurrencyValue | None:
    # TODO: very important to not have mistakes here, make tests for this.
    if strategy == RoundingMethod.UP_1_KEY:
        keys += 1
        metal = 0
    elif strategy == RoundingMethod.NEAREST_5_KEY:
        keys = math.ceil((keys + 1) / 5) * 5
        metal = 0
    elif strategy == RoundingMethod.NEAREST_10_KEY:
        keys = math.ceil((keys + 1) / 10) * 10
        metal = 0
    elif strategy == RoundingMethod.DOWN_1_KEY:
        if keys <= 0:
            return None
        # if competitor has no metal in buyorder, go down a key.
        # If not, just remove metal.
        if not competitor_metal or competitor_metal == 0:
            keys -= 1
        metal = 0
    return CurrencyValue(keys=keys, metal=metal)


async def get_competitor_price(
    db: AsyncSession, listing_id: str, intent: Intent
) -> CurrencyValue | None:
    if intent == Intent.buy:
        buyorder_state = await db.get(models.BuyorderState, listing_id)
        if not buyorder_state:
            return None
        return CurrencyValue(
            keys=buyorder_state.top_competitor_keys,
            metal=buyorder_state.top_competitor_metal,
        )
    elif intent == Intent.sell:
        sellorder_state = await db.get(models.SellorderState, listing_id)
        if not sellorder_state:
            return None
        return CurrencyValue(
            keys=sellorder_state.lowest_competitor_keys,
            metal=sellorder_state.lowest_competitor_metal,
        )


async def update_order_price(
    db: AsyncSession, listing: models.Listing
) -> models.BuyorderState | models.SellorderState | None:
    if listing.intent == Intent.buy:
        state = await db.get(models.BuyorderState, listing.id)
    else:
        state = await db.get(models.SellorderState, listing.id)
    if not state:
        return None

    old_state = copy.deepcopy(state)
    state.user_keys = listing.keys
    state.user_metal = listing.metal

    if listing.intent == Intent.buy:
        assert isinstance(state, models.BuyorderState)  # to fix pyright issues
        assert isinstance(old_state, models.BuyorderState)
        if CurrencyValue(keys=state.user_keys, metal=state.user_metal) >= CurrencyValue(
            keys=state.top_competitor_keys,
            metal=state.top_competitor_metal,
        ):
            state.is_outbid = False
            state.outbid_by = None
        if old_state.is_same_as(state):
            return old_state
    else:
        assert isinstance(state, models.SellorderState)
        assert isinstance(old_state, models.SellorderState)
        if CurrencyValue(keys=state.user_keys, metal=state.user_metal) <= CurrencyValue(
            keys=state.lowest_competitor_keys, metal=state.lowest_competitor_metal
        ):
            state.is_undercut = False
            state.undercut_by = None
        # duplicate here in if statement to avoid pyright complaint
        if old_state.is_same_as(state):
            return old_state

    state = await db.merge(state)

    if listing.intent == Intent.buy:
        assert isinstance(state, models.BuyorderState)
        assert isinstance(old_state, models.BuyorderState)
        await save_buyorder_state_history(db, old_state, state)
    await db.commit()
    logger.debug("Updated state for order for item %s", listing.item.name)
    return state
