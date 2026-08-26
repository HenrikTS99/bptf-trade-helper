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
    def __init__(self, steamid: str, bp: BackpackTFClient):
        self.bp = bp
        # TODO: get user steamid
        self.steamid = steamid

    async def fetch_item_listings(self, item_name: str) -> list[SnapshotBPListing]:
        item_listings = await self.bp.get_snapshot(item_name)
        return item_listings

    def resolve_users_price(self, orders: list[SnapshotBPListing]) -> CurrencyValue:
        users_order = next(
            (listing for listing in orders if listing.steamid == self.steamid), None
        )
        if not users_order:
            raise BuyorderError("users buyorder not found")
        return users_order.currencies

    def get_highest_competitor_buyorder(
        self, buyorders: list[SnapshotBPListing]
    ) -> SnapshotBPListing | None:
        return self._highest_buyorder(buyorders, exclude_own=True)

    def get_highest_buyorder(
        self, buyorders: list[SnapshotBPListing]
    ) -> SnapshotBPListing | None:
        return self._highest_buyorder(buyorders)

    def _highest_buyorder(
        self, orders: list[SnapshotBPListing], exclude_own: bool = False
    ) -> SnapshotBPListing | None:
        highest = None
        for order in orders:
            # Ignore items listed in dollars (marketplace.tf)
            if order.currencies.keys == 0 and order.currencies.metal == 0:
                continue
            if order.is_spelled:
                continue
            if exclude_own and order.steamid == self.steamid:
                continue
            if highest is None or order.currencies > highest.currencies:
                highest = order
        return highest

    def get_lowest_competitor_sellorder(
        self, sellorders: list[SnapshotBPListing]
    ) -> SnapshotBPListing | None:
        return self._lowest_sellorder(sellorders, exclude_own=True)

    def get_lowest_sellorder(
        self, sellorders: list[SnapshotBPListing]
    ) -> SnapshotBPListing | None:
        return self._lowest_sellorder(sellorders)

    def _lowest_sellorder(
        self, orders: list[SnapshotBPListing], exclude_own: bool = False
    ) -> SnapshotBPListing | None:
        lowest = None
        for order in orders:
            # Ignore items listed in dollars (marketplace.tf)
            if order.currencies.keys == 0 and order.currencies.metal == 0:
                continue
            if exclude_own and order.steamid == self.steamid:
                continue
            if lowest is None or order.currencies < lowest.currencies:
                lowest = order
        return lowest
