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

    async def _fetch_item_buyorders(self, item_name: str) -> list[SnapshotBPListing]:
        item_listings = await self.bp.get_snapshot(item_name)
        buyorders = [listing for listing in item_listings if listing.intent == "buy"]
        return buyorders

    def _resolve_users_price(self, buyorders: list[SnapshotBPListing]) -> CurrencyValue:
        users_buyorder = next((b for b in buyorders if b.steamid == self.steamid), None)
        if not users_buyorder:
            raise BuyorderError("users buyorder not found")
        return users_buyorder.currencies

    def _get_highest_competitor_buyorder(
        self, buyorders: list[SnapshotBPListing]
    ) -> SnapshotBPListing | None:
        highest = None
        for order in buyorders:
            if order.steamid == self.steamid or order.isSpelled:
                continue
            if highest is None or order.currencies > highest.currencies:
                highest = order
        return highest

    # def _outbids_user(
    #     self, buyorder: SnapshotBPListing, users_price: CurrencyValue
    # ) -> bool:
    #     if buyorder.steamid == self.steamid or buyorder.isSpelled:
    #         return False
    #     if buyorder.currencies > users_price:
    #         return True
    #     return False

    # def _build_buyorder_data(
    #     self,
    #     item_name: str,
    #     users_price: CurrencyValue,
    #     top_competitor_buyorder: SnapshotBPListing | None,
    # ) -> BuyorderData:
    #     outbid = False
    #     if top_competitor_buyorder:
    #         outbid = users_price < top_competitor_buyorder.currencies
    #     buyorder_data = BuyorderData(
    #         steamid=self.steamid,
    #         outbid_by=None,
    #         name=item_name,
    #         users_price=users_price,
    #         top_competitor_price=top_competitor_buyorder,
    #         outbid=outbid,
    #     )
    #     if outbid and top_competitor_buyorder:
    #         buyorder_data.outbid_by = top_competitor_buyorder.steamid
    #     return buyorder_data
