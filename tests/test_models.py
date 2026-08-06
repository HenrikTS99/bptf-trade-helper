import pytest

from app.models.enums import Intent
from app.models.listings import BPListing, CurrencyValue, SnapshotBPListing

API_LISTING = {
    "id": "1;2;3;4",
    "steamid": "76561198000000000",
    "intent": "buy",
    "count": 1,
    "status": "active",
    "currencies": {"keys": 2500, "metal": 0},
    "details": "add me",
    "item": {
        "defindex": 5021,
        "name": "Burning Flames Exquisite Rack",
        "baseName": "Exquisite Rack",
        "quality": {"name": "Unusual", "id": 6},
        "particle": {"name": "Burning Flames", "id": 89},
        "spells": [{"name": "Chromatic Corruption", "defindex": 1004}],
        "craftable": 1,
    },
    "listedAt": 1710000000,
}

MINIMAL_ITEM = {
    "id": "9;8;7;6",
    "steamid": "76561198000000001",
    "intent": "sell",
    "count": 1,
    "status": "active",
    "details": None,
    "listedAt": 1710000001,
    "item": {"defindex": 5021, "name": "Team Captain", "baseName": "Team Captain"},
}


# CurrencyValue tests
def test_keys_decide_before_metal():
    assert CurrencyValue(keys=2, metal=0) > CurrencyValue(keys=1, metal=100)


def test_more_metal():
    assert CurrencyValue(keys=2, metal=5) > CurrencyValue(keys=2, metal=3)


def test_lower_metal():
    assert not CurrencyValue(keys=2, metal=5) > CurrencyValue(keys=2, metal=7)


def test_same_metal_gt():
    assert not CurrencyValue(keys=2, metal=7) > CurrencyValue(keys=2, metal=7)


def test_same_metal_ge():
    assert CurrencyValue(keys=2, metal=7) >= CurrencyValue(keys=2, metal=7)


def test_none_keys_treated_as_0():
    assert CurrencyValue(keys=None, metal=100) > CurrencyValue(keys=0, metal=7)


def test_none_metal_treated_as_0():
    assert not CurrencyValue(keys=2, metal=None) > CurrencyValue(keys=2, metal=0)


# BPListing
def test_bplisting_from_api():
    listing = BPListing.from_api(API_LISTING)
    assert listing.id == API_LISTING["id"]
    assert listing.steamid == API_LISTING["steamid"]
    assert listing.intent == Intent.buy
    assert listing.count == API_LISTING["count"]
    assert listing.status == API_LISTING["status"]
    assert listing.currencies == CurrencyValue(keys=2500, metal=0)
    assert listing.details == API_LISTING["details"]
    assert listing.item.name == "Burning Flames Exquisite Rack"
    assert listing.item.quality == "Unusual"
    assert listing.item.particle == "Burning Flames"
    assert listing.item.spells == ["Chromatic Corruption"]
    assert (
        listing.item_url
        == "https://backpack.tf/classifieds?item=Exquisite+Rack&quality=6&craftable=1&particle=89"
    )


def test_bplisting_from_api_missing_item_defaults():
    listing = BPListing.from_api(MINIMAL_ITEM)
    assert listing.item.quality == ""
    assert listing.item.particle is None
    assert listing.item.spells == []
    assert listing.currencies == CurrencyValue(keys=0, metal=0)
    assert listing.item_url == (
        "https://backpack.tf/classifieds?item=Team+Captain&quality=6&craftable=-1"
    )


def test_build_classifieds_url_without_particle():
    item = {"baseName": "Team Captain", "quality": {"id": 5}, "craftable": 0}
    assert BPListing._build_classifieds_url(item) == (
        "https://backpack.tf/classifieds?item=Team+Captain&quality=5&craftable=0"
    )


# SnapshotBPListing
def test_snapshot_from_api():
    data = {
        "steamid": "76561198000000001",
        "intent": "sell",
        "currencies": {"keys": 10, "metal": 0},
        "details": None,
        "item": {"attributes": [{"defindex": 1004}]},
    }
    snap = SnapshotBPListing.from_api(data, "Community Sparkle Mann Co. Cap")
    assert snap.steamid == data["steamid"]
    assert snap.intent == Intent.sell
    assert snap.currencies == CurrencyValue(keys=10, metal=0)
    assert snap.details is None
    assert snap.is_spelled is True
    assert snap.item_name == "Community Sparkle Mann Co. Cap"


@pytest.mark.parametrize(
    "attrs",
    [
        [{"defindex": 1004}],
        [{"defindex": 1005}],
        [{"defindex": 1006}],
        [{"defindex": "1004"}],
        [{"defindex": 200}, {"defindex": 1004}],
    ],
)
def test_has_spell_true(attrs):
    assert SnapshotBPListing.has_spell(attrs)


@pytest.mark.parametrize("attrs", [[], [{"defindex": 1003}], [{"defindex": 200}]])
def test_has_spell_false(attrs):
    assert not SnapshotBPListing.has_spell(attrs)
