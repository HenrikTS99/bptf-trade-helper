from app.config import Settings
from fastapi import FastAPI, Query
from app.core.bp_client import BackpackTFClient
from app.core.scanner import Scanner
from app.models.enums import Intent


settings = Settings()
bp = BackpackTFClient(settings.bp_api_key, settings.bp_token)
scanner = Scanner(bp)

app = FastAPI()


@app.get("/prices")
async def prices():
    return await bp.get_prices()


@app.get("/listings")
async def listings(
    intent: Intent | None = Query(default=None),
    raw: bool = Query(default=False),
    limit: int = Query(default=1000),
):
    return await bp.get_listings(intent=intent, raw=raw, limit=limit)


@app.get("/listings/item")
async def snapshot(
    sku: str,
    intent: Intent | None = Query(default=None),
    raw: bool = Query(default=False),
):
    return await bp.get_snapshot(sku, intent=intent, raw=raw)


@app.get("/beatenBuyorders")
async def beatenBuyorders(limit: int = Query(default=10)):
    return await scanner.find_outbids(limit=limit)
