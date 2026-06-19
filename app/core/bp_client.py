from app.models.listings import BPListing, SnapshotBPListing
import httpx
import asyncio
import logging

logger = logging.getLogger(__name__)


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
    ) -> tuple[list[BPListing], dict | None]:
        params = {"key": self.api_key, "limit": limit}
        return await self._fetch_listings(
            "/v2/classifieds/listings",
            params=params,
            parser=BPListing.from_api,
            intent=intent,
            raw=raw,
        )

    async def get_snapshot(
        self, sku: str, intent: str | None = None, raw: bool = False
    ) -> list[SnapshotBPListing]:
        def parse(data):
            return SnapshotBPListing.from_api(data, sku)

        logger.info("fetching snapshot for item:%s", sku)

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
        retry_delays = [1, 2, 5, 10]
        for attempt in range(len(retry_delays)):
            try:
                res = await self.client.get(path, params=params, headers=headers)
                if res.status_code == 429:
                    try:
                        wait = int(res.headers.get("Retry-After", attempt))
                        logger.warning("Rate limited on %s, waiting %ds", path, wait)
                    except ValueError:
                        wait = attempt
                    print("rate limited, waiting: ", wait)
                    await asyncio.sleep(wait)
                    continue
                res.raise_for_status()
                logger.debug("GET %s returned %d", path, res.status_code)
                return res.json()
            except httpx.TimeoutException:
                raise BackpackTFError("Request timed out")
            except httpx.HTTPStatusError as e:
                raise BackpackTFError(f"HTTP {e.response.status_code}")
        logger.error("Rate limited after %d retries on %s", len(retry_delays), path)
        raise RateLimitedError(f"Rate limited after {len(retry_delays)} retries")
