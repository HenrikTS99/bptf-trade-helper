from app import crud
from app.db import models
from app.models.enums import Intent
from app.models.listings import BPListing, CurrencyValue, ItemData


async def seed_listing(db_session, listing_id="L1", intent=Intent.buy):
    item = models.Item(defindex=5021, name="Key", quality="Unique", particle=None)
    db_session.add(item)
    await db_session.flush()
    listing = models.Listing(
        id=listing_id,
        steamid="s",
        intent=intent,
        status="active",
        keys=5,
        metal=0.0,
        item_id=item.id,
        item_url="u",
    )
    db_session.add(listing)
    await db_session.commit()
    return listing, item


async def seed_buyorder_state(db_session, listing_id="L1", is_outbid=True):
    await seed_listing(db_session, listing_id)
    state = models.BuyorderState(
        listing_id=listing_id,
        steamid="s",
        item_name="Key",
        user_keys=5,
        user_metal=0.0,
        top_competitor_keys=10,
        top_competitor_metal=0.0,
        is_outbid=is_outbid,
        lowest_seller_keys=2,
        lowest_seller_metal=0.0,
    )
    db_session.add(state)
    await db_session.commit()
    return state


async def seed_sellorder_state(db_session, listing_id="L1", is_undercut=True):
    await seed_listing(db_session, listing_id)
    state = models.SellorderState(
        listing_id=listing_id,
        steamid="s",
        item_name="Key",
        user_keys=5,
        user_metal=0.0,
        lowest_competitor_keys=10,
        lowest_competitor_metal=0.0,
        is_undercut=is_undercut,
        highest_buyer_keys=2,
        highest_buyer_metal=0.0,
    )
    db_session.add(state)
    await db_session.commit()
    return state


def listing_dict(id="L2"):
    return {
        "id": id,
        "steamid": "s",
        "intent": "buy",
        "count": 1,
        "status": "active",
        "currencies": {"keys": 5, "metal": 0.0},
        "item": {
            "defindex": 5021,
            "name": "Key",
            "baseName": "Key",
            "quality": {"name": "Unique", "id": 6},
            "spells": [],
        },
        "listedAt": 1,
    }


async def test_get_stored_listings(db_session):
    await seed_listing(db_session, "L1", Intent.buy)
    await seed_listing(db_session, "L2", Intent.sell)
    all_listings = await crud.get_stored_listings(db_session)
    assert len(all_listings) == 2
    assert all_listings[0].item.name == "Key"  # joinedload works
    buy = await crud.get_stored_listings(db_session, intent=Intent.buy)
    sell = await crud.get_stored_listings(db_session, intent=Intent.sell)
    assert [listing.id for listing in buy] == ["L1"]
    assert [listing.id for listing in sell] == ["L2"]


async def test_get_listing_by_id_and_status(db_session):
    await seed_listing(db_session)
    found = await crud.get_listing(db_session, "L1")
    assert found is not None and found.id == "L1"
    assert await crud.get_listing(db_session, "L1", status="inactive") is None
    assert await crud.get_listing(db_session, "nope") is None


async def test_get_or_create_item_creates_and_reuses(db_session):
    item_data = ItemData(defindex=5021, name="Key", base_name="Key", quality="Unique")
    first = await crud.get_or_create_item(db_session, item_data)
    second = await crud.get_or_create_item(db_session, item_data)
    assert first.id is not None
    assert second.id == first.id


async def test_upsert_listing_creates(db_session):
    _, item = await seed_listing(db_session)
    await crud.upsert_listing(db_session, BPListing.from_api(listing_dict()), item.id)
    await db_session.commit()
    stored = await crud.get_stored_listings(db_session)
    assert sorted(listing.id for listing in stored) == ["L1", "L2"]


async def test_upsert_listing_unchanged(db_session):
    _, item = await seed_listing(db_session)
    bp_listing = BPListing.from_api(listing_dict())
    first = await crud.upsert_listing(db_session, bp_listing, item.id)
    await db_session.commit()
    second = await crud.upsert_listing(db_session, bp_listing, item.id)
    assert second is first
    assert second.keys == 5 and second.metal == 0.0


async def test_upsert_listing_updates_price(db_session):
    _, item = await seed_listing(db_session)
    await crud.upsert_listing(db_session, BPListing.from_api(listing_dict()), item.id)
    changed = BPListing.from_api(listing_dict()).model_copy(
        update={"currencies": CurrencyValue(keys=9, metal=1.0)}
    )
    await crud.upsert_listing(db_session, changed, item.id)
    await db_session.commit()
    stored = await crud.get_stored_listings(db_session)
    updated = next(listing for listing in stored if listing.id == "L2")
    assert updated.keys == 9 and updated.metal == 1.0


async def test_get_stored_buyorder_states_filter(db_session):
    await seed_buyorder_state(db_session, "L1", is_outbid=True)
    await seed_buyorder_state(db_session, "L2", is_outbid=False)
    all_states = await crud.get_stored_buyorder_states(db_session)
    assert len(all_states) == 2
    beaten = await crud.get_stored_buyorder_states(db_session, only_beaten=True)
    assert [s.listing_id for s in beaten] == ["L1"]
    assert beaten[0].listing.item.name == "Key"


async def test_get_buyorder_states_by_ids(db_session):
    await seed_buyorder_state(db_session, "L1")
    await seed_buyorder_state(db_session, "L2")
    states = await crud.get_buyorder_states_by_ids(db_session, ["L1"])
    assert [s.listing_id for s in states] == ["L1"]


async def test_get_stored_sellorder_states_filter(db_session):
    await seed_sellorder_state(db_session, "L1", is_undercut=True)
    await seed_sellorder_state(db_session, "L2", is_undercut=False)
    all_states = await crud.get_stored_sellorder_states(db_session)
    assert len(all_states) == 2
    beaten = await crud.get_stored_sellorder_states(db_session, only_beaten=True)
    assert [s.listing_id for s in beaten] == ["L1"]
    assert beaten[0].listing.item.name == "Key"


async def test_get_sellorder_states_by_ids(db_session):
    await seed_sellorder_state(db_session, "L1")
    await seed_sellorder_state(db_session, "L2")
    states = await crud.get_sellorder_states_by_ids(db_session, ["L1"])
    assert [s.listing_id for s in states] == ["L1"]


async def test_save_buyorder_state_history_flags(db_session):
    await seed_listing(db_session)
    old = models.BuyorderState(listing_id="L1", steamid="s", item_name="Key")
    new = models.BuyorderState(listing_id="L1", steamid="s", item_name="Key")
    for s in (old, new):
        s.user_keys = 1
        s.user_metal = 0.0
        s.top_competitor_keys = 10
        s.top_competitor_metal = 0.0
        s.is_outbid = True
        s.lowest_seller_keys = 2
        s.lowest_seller_metal = 0.0
    new.user_keys = 3
    new.top_competitor_keys = 12
    new.is_outbid = False
    new.lowest_seller_keys = 4
    await crud.save_buyorder_state_history(db_session, old, new)
    await db_session.commit()
    histories = await crud.get_stored_buyorder_state_histories(db_session)
    assert len(histories) == 1
    h = histories[0]
    assert h.old_user_keys == 1 and h.new_user_keys == 3
    assert h.old_top_competitor_keys == 10 and h.new_top_competitor_keys == 12
    assert h.old_is_outbid is True and h.new_is_outbid is False
    assert h.old_lowest_seller_keys == 2 and h.new_lowest_seller_keys == 4
    assert h.outbid_changed is True
    assert h.regained_top_changed is True
    assert h.competitor_price_changed is True
    assert h.price_updated_changed is True
    assert h.lowest_seller_changed is True


async def test_save_sellorder_state_history_flags(db_session):
    await seed_listing(db_session)
    old = models.SellorderState(listing_id="L1", steamid="s", item_name="Key")
    new = models.SellorderState(listing_id="L1", steamid="s", item_name="Key")
    for s in (old, new):
        s.user_keys = 1
        s.user_metal = 0.0
        s.lowest_competitor_keys = 10
        s.lowest_competitor_metal = 0.0
        s.is_undercut = True
        s.highest_buyer_keys = 2
        s.highest_buyer_metal = 0.0
    new.user_keys = 3
    new.lowest_competitor_keys = 12
    new.is_undercut = False
    new.highest_buyer_keys = 4
    await crud.save_sellorder_state_history(db_session, old, new)
    await db_session.commit()
    histories = await crud.get_stored_sellorder_state_histories(db_session)
    assert len(histories) == 1
    h = histories[0]
    assert h.undercut_changed is True
    assert h.regained_lowest_changed is True
    assert h.competitor_price_changed is True
    assert h.price_updated_changed is True
    assert h.highest_buyer_changed is True


async def test_get_buyorder_state_histories_filter_flags(db_session):
    await seed_listing(db_session)
    old = models.BuyorderState(listing_id="L1", steamid="s", item_name="Key")
    new = models.BuyorderState(listing_id="L1", steamid="s", item_name="Key")
    for s in (old, new):
        s.user_keys = 1
        s.user_metal = 0.0
        s.top_competitor_keys = 10
        s.top_competitor_metal = 0.0
        s.is_outbid = True
        s.lowest_seller_keys = 2
        s.lowest_seller_metal = 0.0
    old.is_outbid = False  # only the outbid flag changes (False -> True)
    await crud.save_buyorder_state_history(db_session, old, new)
    await db_session.commit()
    outbid_only = await crud.get_stored_buyorder_state_histories(
        db_session,
        outbid=True,
        regained_top=False,
        competitor_price=False,
        price_updated=False,
        lowest_seller=False,
    )
    assert len(outbid_only) == 1
    no_match = await crud.get_stored_buyorder_state_histories(
        db_session,
        outbid=False,
        regained_top=False,
        competitor_price=True,
        price_updated=False,
        lowest_seller=False,
    )
    assert len(no_match) == 0
