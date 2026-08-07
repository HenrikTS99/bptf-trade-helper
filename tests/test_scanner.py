from typing import cast

import pytest

from app.core.bp_client import BackpackTFClient
from app.core.scanner import BuyorderError, Scanner
from app.models.enums import Intent
from app.models.listings import CurrencyValue, SnapshotBPListing

USER = "76561198061440669"


def make_scanner() -> Scanner:
    return Scanner(bp=cast(BackpackTFClient, None))


def snap(steamid, keys, metal=0.0, spelled=False):
    return SnapshotBPListing(
        steamid=steamid,
        intent=Intent.buy,
        currencies=CurrencyValue(keys=keys, metal=metal),
        is_spelled=spelled,
        item_name="x",
    )


def test_resolve_users_price_finds_own_order():
    s = make_scanner()
    orders = [snap("order1", 1), snap(USER, 5, 10), snap("other2", 9)]
    assert s.resolve_users_price(orders) == CurrencyValue(keys=5, metal=10)


def test_resolve_users_price_raises_when_absent():
    s = make_scanner()
    with pytest.raises(BuyorderError):
        s.resolve_users_price([snap("other1", 1)])


def test_highest_competitor_buyorder():
    s = make_scanner()
    orders = [snap("a", 2), snap("b", 5), snap("c", 3, spelled=True)]
    result = s.get_highest_competitor_buyorder(orders)
    assert result is not None
    assert result.steamid == "b"


def test_highest_competitor_buyorder_skips_own_and_spelled():
    s = make_scanner()
    orders = [snap(USER, 99), snap("a", 2, spelled=True)]
    assert s.get_highest_competitor_buyorder(orders) is None


def test_highest_competitor_buyorder_empty():
    s = make_scanner()
    assert s.get_highest_competitor_buyorder([]) is None


def test_highest_buyorder_skips_dollar_listings():
    s = make_scanner()
    orders = [snap("a", 0, 0)]
    result = s.get_highest_buyorder(orders)
    assert result is None


def test_highest_buyorder_includes_own():
    s = make_scanner()
    orders = [snap("a", 2), snap(USER, 5)]
    result = s.get_highest_buyorder(orders)
    assert result is not None
    assert result.steamid == USER


def test_highest_buyorder_excludes_spelled():
    s = make_scanner()
    orders = [snap("a", 2), snap("c", 9, spelled=True)]
    result = s.get_highest_buyorder(orders)
    assert result is not None
    assert result.steamid == "a"


def test_highest_buyorder_empty():
    s = make_scanner()
    assert s.get_highest_buyorder([]) is None


def test_lowest_competitor_sellorder():
    s = make_scanner()
    orders = [snap("a", 5), snap(USER, 1), snap("b", 3), snap("c", 4, spelled=True)]
    result = s.get_lowest_competitor_sellorder(orders)
    assert result is not None
    assert result.steamid == "b"


def test_lowest_sellorder_includes_own():
    s = make_scanner()
    orders = [snap("a", 5), snap(USER, 1), snap("c", 4, spelled=True)]
    result = s.get_lowest_sellorder(orders)
    assert result is not None
    assert result.steamid == USER


def test_lowest_sellorder_skips_dollar_listings():
    s = make_scanner()
    orders = [snap("a", 0, 0), snap("b", 5), snap("c", 3)]
    result = s.get_lowest_sellorder(orders)
    assert result is not None
    assert result.steamid == "c"


def test_lowest_sellorder_empty():
    s = make_scanner()
    assert s.get_lowest_sellorder([]) is None


def test_lowest_competitor_sellorder_includes_spelled():
    s = make_scanner()
    orders = [snap("a", 5), snap(USER, 3), snap("c", 1, spelled=True)]
    result = s.get_lowest_competitor_sellorder(orders)
    assert result is not None
    assert result.steamid == "c"


def test_lowest_competitor_sellorder_skips_dollar():
    s = make_scanner()
    orders = [snap("a", 0, 0), snap(USER, 4), snap("b", 2)]
    result = s.get_lowest_competitor_sellorder(orders)
    assert result is not None
    assert result.steamid == "b"


def test_lowest_competitor_sellorder_empty():
    s = make_scanner()
    assert s.get_lowest_competitor_sellorder([]) is None
