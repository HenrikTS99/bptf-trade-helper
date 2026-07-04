from fastapi import APIRouter, Request, Depends, HTTPException, Query, status
from app.scheduler import scheduler
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.core.sync_tracker import sync_tracker

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.listing_service import (
    update_listing_price,
    update_buyorder_price,
)

from app.crud import get_stored_buyorder_states
from app.db.base import get_db
from app.crud import get_listing
from app.dependencies import bp

from app.models.enums import RoundingMethod

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def display_dashboard(
    request: Request,
    only_beaten: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
):
    buyorders = await get_stored_buyorder_states(db, only_beaten=only_beaten)
    return templates.TemplateResponse(
        request=request,
        name="pages/dashboard.html",
        context={
            "beaten_buyorders": buyorders,
            "only_beaten": only_beaten,
            "tracker": sync_tracker,
        },
    )


@router.patch("/listings/{listing_id}/round-price")
async def round_listing_price(
    request: Request,
    listing_id: str,
    rounding_strategy: RoundingMethod = Query(default=RoundingMethod.UP_1_KEY),
    db: AsyncSession = Depends(get_db),
):
    listing = await get_listing(db, listing_id)
    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Listing with ID {listing_id} does not exist",
        )
    updated_listing = await update_listing_price(db, listing, rounding_strategy, bp)
    if not updated_listing:
        raise HTTPException(
            status_code=409,
            detail=f"Update to listing price for Listing with ID {listing_id} failed.",
        )
    updated_buyorder_state = await update_buyorder_price(db, updated_listing)
    if not updated_buyorder_state:
        raise HTTPException(
            status_code=409,
            detail=f"Update to buyorder state for Listing with ID {listing_id} failed.",
        )
    # Refresh required after merge/commit to avoid MissingGreenlet error (accessing expired attributes cause error)
    await db.refresh(updated_buyorder_state)
    return templates.TemplateResponse(
        request=request,
        name="partials/buyorder_row.html",
        context={"bo": updated_buyorder_state},
    )


@router.post("/buyorder_states/refresh", response_class=HTMLResponse)
async def update_buyorder_states(request: Request):
    if not sync_tracker.is_syncing:
        scheduler.modify_job("run_scheduled_sync", next_run_time=datetime.now())
        sync_tracker.start()
    return templates.TemplateResponse(
        request=request,
        name="partials/sync_status.html",
        context={"tracker": sync_tracker},
    )


@router.get("/sync-status", response_class=HTMLResponse)
async def sync_status(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="partials/sync_status.html",
        context={"tracker": sync_tracker},
    )
