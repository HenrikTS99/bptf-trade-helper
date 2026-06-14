from .bp_client import BackpackTFClient


class Scanner:
    def __init__(self, bp: BackpackTFClient):
        self.bp = bp
        self._snapshot_cache: dict[str, list]
        # TODO: get user steamid
        self.steamid = "76561198061440669"

    async def find_beaten_orders(self) -> list[dict]:
        orders, _ = await self.bp.get_listings(intent="buy", limit=10)
        beaten_orders = []
        for order in orders:
            print("name: " + order.item.name)
            item_listings = await self.bp.get_snapshot(order.item.name)
            buyorders = [
                listing for listing in item_listings if listing.intent == "buy"
            ]
            users_buyorder = next(
                (b for b in buyorders if b.steamid == self.steamid), None
            )
            print(users_buyorder)
            if not users_buyorder:
                # TODO
                raise ValueError
            order_info = {
                "name": order.item.name,
                "users_price": order.currencies,
                "highest_price": order.currencies,
            }

            outbid = False
            for buyorder in buyorders:
                if buyorder.steamid == self.steamid or buyorder.isSpelled:
                    continue
                if buyorder.currencies > users_buyorder.currencies:
                    outbid = True
                    if buyorder.currencies > order_info["highest_price"]:
                        order_info["highest_price"] = buyorder.currencies
                order_info["steamid"] = order.steamid

            order_info["outbid"] = outbid
            beaten_orders.append(order_info)
        return beaten_orders
