from app.db.models import BuyorderState, SellorderState
from app.models.enums import Intent
from app.models.listings import CurrencyValue, SnapshotBPListing
from app.services.scanner_service import _apply_buyorder_values, _apply_sellorder_values


def competitor(steamid, keys, metal=0.0, spelled=False, intent=Intent.buy):
    return SnapshotBPListing(
        steamid=steamid,
        intent=intent,
        currencies=CurrencyValue(keys=keys, metal=metal),
        is_spelled=spelled,
        item_name="x",
    )


def test_buyorder_maps_user_price():
    state = BuyorderState(listing_id="1", steamid="s", item_name="x")
    _apply_buyorder_values(state, CurrencyValue(keys=5, metal=12.5), None, None)
    assert state.user_keys == 5
    assert state.user_metal == 12.5


def test_buyorder_none_keys_to_zero():
    state = BuyorderState(listing_id="1", steamid="s", item_name="x")
    _apply_buyorder_values(state, CurrencyValue(keys=None, metal=None), None, None)
    assert state.user_keys == 0
    assert state.user_metal is None


def test_buyorder_is_outbid_true():
    state = BuyorderState(listing_id="1", steamid="s", item_name="x")
    _apply_buyorder_values(
        state, CurrencyValue(keys=5, metal=12.5), competitor("id1", 6, 0), None
    )
    assert state.is_outbid is True
    assert state.outbid_by == "id1"
    assert state.top_competitor_keys == 6
    assert state.top_competitor_metal == 0


def test_buyorder_is_outbid_false():
    state = BuyorderState(listing_id="1", steamid="s", item_name="x")
    _apply_buyorder_values(
        state, CurrencyValue(keys=5, metal=12.5), competitor("id1", 5, 0), None
    )
    assert state.is_outbid is False


def test_buyorder_comp_keys_none_to_zero():
    state = BuyorderState(listing_id="1", steamid="s", item_name="x")
    _apply_buyorder_values(
        state, CurrencyValue(keys=5, metal=12.5), competitor("id1", None, 50), None
    )
    assert state.top_competitor_keys == 0


def test_buyorder_competitor_absent_untouched():
    state = BuyorderState(listing_id="1", steamid="s", item_name="x")
    state.top_competitor_keys = 99
    state.top_competitor_metal = 1.0
    _apply_buyorder_values(state, CurrencyValue(keys=5, metal=12.5), None, None)
    assert state.top_competitor_keys == 99
    assert state.top_competitor_metal == 1.0


def test_buyorder_lowest_seller_mapped():
    state = BuyorderState(listing_id="1", steamid="s", item_name="x")
    _apply_buyorder_values(
        state,
        CurrencyValue(keys=None, metal=None),
        None,
        CurrencyValue(keys=5, metal=6),
    )
    assert state.lowest_seller_keys == 5
    assert state.lowest_seller_metal == 6


def test_buyorder_lowest_seller_absent_untouched():
    state = BuyorderState(listing_id="1", steamid="s", item_name="x")
    state.lowest_seller_keys = 10
    state.lowest_seller_metal = 11
    _apply_buyorder_values(state, CurrencyValue(keys=5, metal=12.5), None, None)
    assert state.lowest_seller_keys == 10
    assert state.lowest_seller_metal == 11


# Sellorder
def test_sellorder_maps_user_price():
    state = SellorderState(listing_id="1", steamid="s", item_name="x")
    _apply_sellorder_values(state, CurrencyValue(keys=5, metal=12.5), None, None)
    assert state.user_keys == 5
    assert state.user_metal == 12.5


def test_sellorder_is_undercut_true():
    state = SellorderState(listing_id="1", steamid="s", item_name="x")
    _apply_sellorder_values(
        state, CurrencyValue(keys=4, metal=0), competitor("id1", 2, 5), None
    )
    assert state.is_undercut is True
    assert state.undercut_by == "id1"
    assert state.lowest_competitor_keys == 2
    assert state.lowest_competitor_metal == 5


def test_sellorder_is_undercut_false():
    state = SellorderState(listing_id="1", steamid="s", item_name="x")
    _apply_sellorder_values(
        state, CurrencyValue(keys=2, metal=0), competitor("id1", 4, 0), None
    )
    assert state.is_undercut is False


def test_sellorder_competitor_keys_none_kept():
    state = SellorderState(listing_id="1", steamid="s", item_name="x")
    _apply_sellorder_values(
        state, CurrencyValue(keys=4, metal=0), competitor("id1", None, 3), None
    )
    assert state.is_undercut is True
    assert state.lowest_competitor_keys is None


def test_sellorder_competitor_absent_untouched():
    state = SellorderState(listing_id="1", steamid="s", item_name="x")
    state.is_undercut = True
    state.lowest_competitor_keys = 99
    state.lowest_competitor_metal = 1.0
    _apply_sellorder_values(state, CurrencyValue(keys=5, metal=12.5), None, None)
    assert state.is_undercut is True
    assert state.lowest_competitor_keys == 99
    assert state.lowest_competitor_metal == 1.0


def test_sellorder_highest_buyer_mapped():
    state = SellorderState(listing_id="1", steamid="s", item_name="x")
    _apply_sellorder_values(
        state, CurrencyValue(keys=4, metal=0), None, CurrencyValue(keys=10, metal=0)
    )
    assert state.highest_buyer_keys == 10
    assert state.highest_buyer_metal == 0


def test_sellorder_highest_buyer_keys_none():
    state = SellorderState(listing_id="1", steamid="s", item_name="x")
    _apply_sellorder_values(
        state, CurrencyValue(keys=4, metal=0), None, CurrencyValue(keys=None, metal=0)
    )
    assert state.highest_buyer_keys is None


def test_is_same_as_identical_true():
    a = BuyorderState(listing_id="1", steamid="s1", item_name="x")
    b = BuyorderState(listing_id="2", steamid="s2", item_name="x")
    _apply_buyorder_values(
        a,
        CurrencyValue(keys=5, metal=12.5),
        competitor("id1", 6, 0),
        CurrencyValue(keys=1, metal=0),
    )
    _apply_buyorder_values(
        b,
        CurrencyValue(keys=5, metal=12.5),
        competitor("id1", 6, 0),
        CurrencyValue(keys=1, metal=0),
    )
    assert a.is_same_as(b)


def test_is_same_as_different_metal_false():
    a = BuyorderState(listing_id="1", steamid="s", item_name="x")
    b = BuyorderState(listing_id="1", steamid="s", item_name="x")
    _apply_buyorder_values(
        a, CurrencyValue(keys=5, metal=12.5), competitor("id1", 6, 0), None
    )
    _apply_buyorder_values(
        b, CurrencyValue(keys=5, metal=12.5), competitor("id1", 6, 0), None
    )
    b.user_metal = 99
    assert not a.is_same_as(b)


def test_is_same_as_ignores_outbid_by():
    a = BuyorderState(listing_id="1", steamid="s", item_name="x")
    b = BuyorderState(listing_id="1", steamid="s", item_name="x")
    _apply_buyorder_values(
        a, CurrencyValue(keys=5, metal=12.5), competitor("id1", 6, 0), None
    )
    _apply_buyorder_values(
        b, CurrencyValue(keys=5, metal=12.5), competitor("id2", 6, 0), None
    )
    assert a.is_same_as(b)
