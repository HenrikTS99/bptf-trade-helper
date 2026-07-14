from enum import StrEnum


class Intent(StrEnum):
    buy = "buy"
    sell = "sell"


class RoundingMethod(StrEnum):
    UP_1_KEY = "up_1-key"
    NEAREST_5_KEY = "nearest_5-key"
    NEAREST_10_KEY = "nearest_10-key"
