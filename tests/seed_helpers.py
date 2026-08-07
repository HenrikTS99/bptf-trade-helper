from app.db import models
from app.models.enums import Intent


async def seed_listing(
    db_session, listing_id="L1", intent=Intent.buy, keys=5, metal=0.0
):
    item = models.Item(defindex=5021, name="Key", quality="Unique", particle=None)
    db_session.add(item)
    await db_session.flush()
    listing = models.Listing(
        id=listing_id,
        steamid="s",
        intent=intent,
        status="active",
        keys=keys,
        metal=metal,
        item_id=item.id,
        item_url="u",
    )
    db_session.add(listing)
    await db_session.commit()
    return listing, item


async def seed_buyorder_state(
    db_session, listing, user_keys=5, top_competitor_keys=10, is_outbid=True
):
    state = models.BuyorderState(
        listing_id=listing.id,
        steamid="s",
        item_name="Key",
        user_keys=user_keys,
        user_metal=0.0,
        top_competitor_keys=top_competitor_keys,
        top_competitor_metal=0.0,
        is_outbid=is_outbid,
        lowest_seller_keys=2,
        lowest_seller_metal=0.0,
    )
    db_session.add(state)
    await db_session.commit()
    return state


async def seed_sellorder_state(
    db_session,
    listing,
    user_keys=5,
    lowest_competitor_keys=10,
    is_undercut=True,
    highest_buyer_keys=2,
):
    state = models.SellorderState(
        listing_id=listing.id,
        steamid="s",
        item_name="Key",
        user_keys=user_keys,
        user_metal=0.0,
        lowest_competitor_keys=lowest_competitor_keys,
        lowest_competitor_metal=0.0,
        is_undercut=is_undercut,
        highest_buyer_keys=highest_buyer_keys,
        highest_buyer_metal=0.0,
    )
    db_session.add(state)
    await db_session.commit()
    return state
