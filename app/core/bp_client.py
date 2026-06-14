from app.models.listings import Listing, ItemListing
import httpx


class BackpackTFClient:
    def __init__(self, api_key: str, token: str):
        self.api_key = api_key
        self.token = token
        self.client = httpx.AsyncClient(base_url="https://backpack.tf/api")

    async def get_prices(self, raw: int = 1):
        return await self._get(
            "IGetPrices/v4", params={"key": self.api_key, "raw": raw}
        )

    async def get_listings(
        self, intent: str | None = None, raw: bool = False, limit: int = 1000
    ):
        params = {"key": self.api_key, "limit": limit}
        data = await self._get("/v2/classifieds/listings", params=params)
        results = data.get("results", [])
        if intent:
            results = [r for r in results if r["intent"] == intent]
        if raw:
            return results, data.get("cursor")
        return [Listing.from_api(r) for r in results], data.get("cursor")

    async def get_snapshot(
        self, sku: str, intent: str | None = None, raw: bool = False
    ):
        params = {"key": self.api_key, "appid": 440, "sku": sku}
        data = await self._get("classifieds/listings/snapshot", params=params)
        listings = data.get("listings", [])
        if intent:
            listings = [li for li in listings if li["intent"] == intent]
        if raw:
            return listings
        return [ItemListing.from_api(li, sku) for li in listings]

    async def _get(self, path: str, params: dict | None = None):
        headers = {"X-Auth-Token": self.token}
        res = await self.client.get(path, params=params, headers=headers)
        res.raise_for_status()
        return res.json()
