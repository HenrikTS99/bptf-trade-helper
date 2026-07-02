from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.models.enums import Intent
from app.services.listing_service import sync_listings
from app.crud import get_stored_buyorder_states, get_stored_listings, get_listing
from app.models.responses import ListingResponse, BuyorderStateResponse
from app.dependencies import bp

router = APIRouter()


@router.get("/prices")
async def prices():
    return await bp.get_prices()


@router.get("/listings", response_model=list[ListingResponse])
async def listings(
    intent: Intent | None = Query(default=None), db: AsyncSession = Depends(get_db)
):
    return await get_stored_listings(db, intent=intent)


@router.get("/listings/sync")
async def update_listings(
    db: AsyncSession = Depends(get_db),
):
    return await sync_listings(db, bp, sync_all=True)


@router.get("/buyorder_states", response_model=list[BuyorderStateResponse])
async def stored_buyorder_states(
    only_beaten: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
):
    return await get_stored_buyorder_states(db, only_beaten=only_beaten)


@router.get("/buyorder_states/total_buyorders_outbid")
async def total_buyorders_outbid(
    db: AsyncSession = Depends(get_db),
):
    buyorder_states = await get_stored_buyorder_states(db, only_beaten=True)
    return len(buyorder_states)


@router.get("/listings/item")
async def snapshot(
    sku: str,
    intent: Intent | None = Query(default=None),
    raw: bool = Query(default=False),
):
    return await bp.get_snapshot(sku, intent=intent, raw=raw)


@router.get("/listings/{id}")
async def get_listing_by_id(id: str, db: AsyncSession = Depends(get_db)):
    return await get_listing(db, id)
