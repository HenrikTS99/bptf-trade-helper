from app.models.listings import Listing, ItemListing
import httpx


class BackpackTFError(Exception):
    pass


class RateLimitedError(BackpackTFError):
    pass


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
    ) -> tuple[list[Listing], dict | None]:
        params = {"key": self.api_key, "limit": limit}
        return await self._fetch_listings(
            "/v2/classifieds/listings",
            params=params,
            parser=Listing.from_api,
            intent=intent,
            raw=raw,
        )

    async def get_snapshot(
        self, sku: str, intent: str | None = None, raw: bool = False
    ) -> list[ItemListing]:
        def parse(data):
            return ItemListing.from_api(data, sku)

        params = {"key": self.api_key, "appid": 440, "sku": sku}
        listings, _ = await self._fetch_listings(
            "/classifieds/listings/snapshot",
            params=params,
            parser=parse,
            intent=intent,
            raw=raw,
        )
        return listings

    async def _fetch_listings(self, path, params, parser, intent, raw):
        data = await self._get(path, params=params)
        results = data.get("listings", data.get("results", []))
        cursor = data.get("cursor")
        if intent:
            results = [r for r in results if r["intent"] == intent]
        if raw:
            return results, cursor
        return [parser(r) for r in results], cursor

    async def _get(self, path: str, params: dict | None = None):
        headers = {"X-Auth-Token": self.token}
        try:
            res = await self.client.get(path, params=params, headers=headers)
            if res.status_code == 429:
                raise RateLimitedError("Rate limited")
            res.raise_for_status()
            return res.json()
        except httpx.TimeoutException:
            raise BackpackTFError("Request timed out")
        except httpx.HTTPStatusError as e:
            raise BackpackTFError(f"HTTP {e.response.status_code}")
