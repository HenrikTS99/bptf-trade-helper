from enum import Enum


class Intent(str, Enum):
    buy = "buy"
    sell = "sell"
