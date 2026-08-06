import pytest

from app.models.enums import RoundingMethod
from app.models.listings import CurrencyValue
from app.services.listing_service import apply_rounding_strategy


def test_match_price():
    result = apply_rounding_strategy(7, 7.66, RoundingMethod.MATCH_PRICE)
    assert result == CurrencyValue(keys=7, metal=7.66)


def test_up_1_key_beats_by_one_key():
    result = apply_rounding_strategy(5, 0.33, RoundingMethod.UP_1_KEY)
    assert result == CurrencyValue(keys=6, metal=0)


@pytest.mark.parametrize(
    "keys, metal, expected",
    [
        (0, 0.0, CurrencyValue(keys=5, metal=0)),
        (1, 0.0, CurrencyValue(keys=5, metal=0)),
        (5, 0.0, CurrencyValue(keys=10, metal=0)),
    ],
)
def test_nearest_5_key(keys, metal, expected):
    result = apply_rounding_strategy(keys, metal, RoundingMethod.NEAREST_5_KEY)
    assert result == expected


@pytest.mark.parametrize(
    "keys, metal, expected",
    [
        (0, 0.0, CurrencyValue(keys=10, metal=0)),
        (1, 0.0, CurrencyValue(keys=10, metal=0)),
        (5, 3.0, CurrencyValue(keys=10, metal=0)),
        (10, 0.0, CurrencyValue(keys=20, metal=0)),
    ],
)
def test_nearest_10_key(keys, metal, expected):
    result = apply_rounding_strategy(keys, metal, RoundingMethod.NEAREST_10_KEY)
    assert result == expected


@pytest.mark.parametrize(
    "keys, metal, expected",
    [
        (0, 0.0, None),
        (1, 0.0, CurrencyValue(keys=0, metal=0)),
        (5, 0.33, CurrencyValue(keys=5, metal=0)),
        (5, 0.0, CurrencyValue(keys=4, metal=0)),
    ],
)
def test_down_1_key(keys, metal, expected):
    result = apply_rounding_strategy(keys, metal, RoundingMethod.DOWN_1_KEY)
    assert result == expected
