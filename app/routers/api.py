from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import (
    get_listing,
    get_stored_buyorder_state_histories,
    get_stored_buyorder_states,
    get_stored_listings,
    get_stored_sellorder_states,
)
from app.db.base import get_db
from app.dependencies import bp, scanner
from app.models.enums import Intent
from app.models.responses import (
    BuyorderStateHistoryResponse,
    BuyorderStateResponse,
    ListingResponse,
    SellorderStateResponse,
)
from app.services.listing_service import sync_listings
from app.services.scanner_service import update_buyorder_data

router = APIRouter()


@router.get("/prices")
async def prices():
    return await bp.get_prices()


@router.get("/listings", response_model=list[ListingResponse])
async def listings(
    intent: Intent | None = Query(default=None), db: AsyncSession = Depends(get_db)
):
    return await get_stored_listings(db, intent=intent)


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


@router.get("/listings/sync")
async def update_listings(
    db: AsyncSession = Depends(get_db),
):
    return await sync_listings(db, bp, sync_all=True)


# BuyorderStates
@router.get("/buyorder_states", response_model=list[BuyorderStateResponse])
async def stored_buyorder_states(
    only_beaten: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
):
    return await get_stored_buyorder_states(db, only_beaten=only_beaten)


@router.post(
    "/buyorder_states/{listing_id}/refresh", response_model=BuyorderStateResponse
)
async def refresh_buyorder_state(listing_id: str, db: AsyncSession = Depends(get_db)):
    listing = await get_listing(db, listing_id)

    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.intent != Intent.buy:
        raise HTTPException(
            status_code=400,
            detail=f"Listing {listing_id} is a sell order, not a buy order",
        )
    buyorder_state, status = await update_buyorder_data(db, scanner, listing)
    if not buyorder_state:
        raise HTTPException(
            status_code=404,
            detail=f"Could not resolve buyorder state for {listing_id}. "
            f"Reason: {status}",
        )
    # refresh all attributes after commit inside update_buyorder_data
    # to prevent MissingGreenlet on serialization
    await db.refresh(buyorder_state)
    await db.refresh(buyorder_state, ["listing"])  # load relationship
    return buyorder_state


@router.get("/buyorder_states/total_buyorders_outbid")
async def total_buyorders_outbid(
    db: AsyncSession = Depends(get_db),
):
    buyorder_states = await get_stored_buyorder_states(db, only_beaten=True)
    return len(buyorder_states)


@router.get(
    "/buyorder_state_histories", response_model=list[BuyorderStateHistoryResponse]
)
async def stored_buyorder_state_histories(
    db: AsyncSession = Depends(get_db),
):
    return await get_stored_buyorder_state_histories(db)


# SellorderStates
@router.get("/sellorder_states", response_model=list[SellorderStateResponse])
async def stored_sellorder_states(
    only_beaten: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
):
    return await get_stored_sellorder_states(db, only_beaten=only_beaten)
