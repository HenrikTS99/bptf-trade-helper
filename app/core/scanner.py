from .bp_client import BackpackTFClient, BackpackTFError
from app.models.listings import CurrencyValue, ItemListing, Listing, BuyorderData
import logging
import asyncio

logger = logging.getLogger(__name__)


class BuyorderError(Exception):
    pass


class Scanner:
    def __init__(self, bp: BackpackTFClient):
        self.bp = bp
        # TODO: get user steamid
        self.steamid = "76561198061440669"

    async def find_outbids(self, limit: int = 10) -> list[BuyorderData]:
        orders, _ = await self.bp.get_listings(intent="buy", limit=limit)
        return await self._find_outbid_orders(orders)

    async def _find_outbid_orders(self, orders: list[Listing]) -> list[BuyorderData]:
        beaten_orders = []
        for order in orders:
            await asyncio.sleep(1)  # for rate limiter
            try:
                buyorders = await self._fetch_item_buyorders(order.item.name)
            except BackpackTFError as e:
                logger.warning(
                    "Failed to fetch snapshot for %s: %s", order.item.name, e
                )
                continue
            try:
                users_price = self._resolve_users_price(buyorders)
            except BuyorderError as e:
                logger.warning(
                    "No buyorder found for %s, skipping. Error: %s", order.item.name, e
                )
                continue
            outbidder = self._find_outbidding_order(buyorders, users_price)
            buyorder_data = self._build_buyorder_data(
                order.item.name, users_price, outbidder
            )
            beaten_orders.append(buyorder_data)
        return beaten_orders

    async def _fetch_item_buyorders(self, item_name: str) -> list[ItemListing]:
        item_listings = await self.bp.get_snapshot(item_name)
        buyorders = [listing for listing in item_listings if listing.intent == "buy"]
        return buyorders

    def _resolve_users_price(self, buyorders: list[ItemListing]) -> CurrencyValue:
        users_buyorder = next((b for b in buyorders if b.steamid == self.steamid), None)
        if not users_buyorder:
            raise BuyorderError("users buyorder not found")
        return users_buyorder.currencies

    def _find_outbidding_order(
        self, buyorders: list[ItemListing], users_price: CurrencyValue
    ) -> ItemListing | None:
        for buyorder in buyorders:
            if self._outbids_user(buyorder, users_price):
                return buyorder
        return None

    def _outbids_user(self, buyorder: ItemListing, users_price: CurrencyValue) -> bool:
        if buyorder.steamid == self.steamid or buyorder.isSpelled:
            return False
        if buyorder.currencies > users_price:
            return True
        return False

    def _build_buyorder_data(
        self, item_name: str, users_price: CurrencyValue, outbidder: ItemListing | None
    ) -> BuyorderData:
        buyorder_data = BuyorderData(
            steamid=self.steamid,
            outbid_by=None,
            name=item_name,
            users_price=users_price,
            highest_price=users_price,
            outbid=False,
        )
        if outbidder:
            buyorder_data.outbid_by = outbidder.steamid
            buyorder_data.highest_price = outbidder.currencies
            buyorder_data.outbid = True
        return buyorder_data
