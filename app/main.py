from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import Settings
from fastapi import FastAPI, Query, Depends
from app.core.bp_client import BackpackTFClient
from app.core.scanner import Scanner
from app.models.enums import Intent
from app.db.base import Base, engine, get_db
from app.services.listing_service import sync_listings, get_stored_listings
import logging

logging.basicConfig(level=logging.INFO)

settings = Settings()
bp = BackpackTFClient(settings.bp_api_key, settings.bp_token)
scanner = Scanner(bp)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/prices")
async def prices():
    return await bp.get_prices()


@app.get("/listings")
async def listings(
    intent: Intent | None = Query(default=None), db: AsyncSession = Depends(get_db)
):
    return await get_stored_listings(db, intent=intent)


@app.get("/listings/sync")
async def update_listings(
    db: AsyncSession = Depends(get_db),
):
    return await sync_listings(db, bp, sync_all=True)


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
