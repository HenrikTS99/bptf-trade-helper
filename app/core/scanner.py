import logging

from app.models.listings import (
    CurrencyValue,
    SnapshotBPListing,
)

from .bp_client import BackpackTFClient

logger = logging.getLogger(__name__)


class BuyorderError(Exception):
    pass


class Scanner:
    def __init__(self, bp: BackpackTFClient):
        self.bp = bp
        # TODO: get user steamid
        self.steamid = "76561198061440669"

    async def fetch_item_listings(self, item_name: str) -> list[SnapshotBPListing]:
        item_listings = await self.bp.get_snapshot(item_name)
        return item_listings

    def resolve_users_price(self, buyorders: list[SnapshotBPListing]) -> CurrencyValue:
        users_buyorder = next((b for b in buyorders if b.steamid == self.steamid), None)
        if not users_buyorder:
            raise BuyorderError("users buyorder not found")
        return users_buyorder.currencies

    def get_highest_competitor_buyorder(
        self, buyorders: list[SnapshotBPListing]
    ) -> SnapshotBPListing | None:
        highest = None
        for order in buyorders:
            if order.steamid == self.steamid or order.is_spelled:
                continue
            if highest is None or order.currencies > highest.currencies:
                highest = order
        return highest

    def get_lowest_sellorder(
        self, sellorders: list[SnapshotBPListing]
    ) -> SnapshotBPListing | None:
        lowest = None
        for order in sellorders:
            # Ignore items listed in dollars (marketplace.tf)
            if order.currencies.keys == 0 and order.currencies.metal == 0:
                continue
            if lowest is None or order.currencies < lowest.currencies:
                lowest = order
        return lowest
