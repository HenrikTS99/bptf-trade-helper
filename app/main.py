import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.bp_client import BackpackTFClient
from app.core.scanner import Scanner
from app.db.base import Base, engine, get_db
from app.models.enums import Intent
from app.services.listing_service import sync_listings
from app.crud import get_stored_buyorder_states, get_stored_listings
from app.scheduler import scheduler, init_scheduler

logging.basicConfig(level=logging.INFO)

settings = Settings()
bp = BackpackTFClient(settings.bp_api_key, settings.bp_token)
scanner = Scanner(bp)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    init_scheduler(bp, scanner)
    scheduler.start()
    yield
    scheduler.shutdown()


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


@app.get("/buyorder_states")
async def stored_buyorder_states(
    only_beaten: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
):
    return await get_stored_buyorder_states(db, only_beaten=only_beaten)


@app.get("/buyorder_states/total_buyorders_outbid")
async def total_buyorders_outbid(
    db: AsyncSession = Depends(get_db),
):
    buyorder_states = await get_stored_buyorder_states(db, only_beaten=True)
    return len(buyorder_states)


@app.get("/listings/item")
async def snapshot(
    sku: str,
    intent: Intent | None = Query(default=None),
    raw: bool = Query(default=False),
):
    return await bp.get_snapshot(sku, intent=intent, raw=raw)
