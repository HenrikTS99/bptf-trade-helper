from enum import Enum


class Intent(str, Enum):
    buy = "buy"
    sell = "sell"


class RoundingMethod(str, Enum):
    UP_1_KEY = "up_1-key"
    NEAREST_5_KEY = "nearest_5-key"
    NEAREST_10_KEY = "nearest_10-key"
