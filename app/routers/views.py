from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.sync_tracker import buy_sync_tracker, sell_sync_tracker
from app.crud import (
    get_listing,
    get_stored_buyorder_state_histories,
    get_stored_buyorder_states,
    get_stored_sellorder_state_histories,
    get_stored_sellorder_states,
)
from app.db.base import get_db
from app.dependencies import bp
from app.models.enums import Intent, RoundingMethod
from app.scheduler import scheduler
from app.services.listing_service import (
    update_listing_price,
    update_order_price,
)

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


@router.get("/buyorders", response_class=HTMLResponse)
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
            "tracker": buy_sync_tracker,
        },
    )


@router.get("/sellorders", response_class=HTMLResponse)
async def display_dashboard_sellorders(
    request: Request,
    only_beaten: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
):
    sellorders = await get_stored_sellorder_states(db, only_beaten=only_beaten)
    return templates.TemplateResponse(
        request=request,
        name="pages/dashboard_sellorders.html",
        context={
            "beaten_sellorders": sellorders,
            "only_beaten": only_beaten,
            "tracker": sell_sync_tracker,
        },
    )


@router.get("/buyorders-history", response_class=HTMLResponse)
async def display_history(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    buyorder_state_histories = await get_stored_buyorder_state_histories(db)
    return templates.TemplateResponse(
        request=request,
        name="pages/buyorder_state_history.html",
        context={
            "buyorder_state_histories": buyorder_state_histories,
        },
    )


@router.get("/sellorders-history", response_class=HTMLResponse)
async def display_sellorder_history(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    sellorder_state_histories = await get_stored_sellorder_state_histories(db)
    return templates.TemplateResponse(
        request=request,
        name="pages/sellorder_state_history.html",
        context={
            "sellorder_state_histories": sellorder_state_histories,
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
    updated_state = await update_order_price(db, updated_listing)
    if listing.intent == Intent.buy:
        template = "partials/buyorder_row.html"
        context_key = "bo"
    else:
        template = "partials/sellorder_row.html"
        context_key = "so"
    if not updated_state:
        raise HTTPException(
            status_code=409,
            detail=f"Update to order state for Listing with ID {listing_id} failed.",
        )
    # Refresh required after merge/commit to avoid MissingGreenlet error
    # (accessing expired attributes cause error)
    await db.refresh(updated_state)
    return templates.TemplateResponse(
        request=request,
        name=template,
        context={context_key: updated_state},
    )


@router.post("/buyorder_states/refresh", response_class=HTMLResponse)
async def update_buyorder_states(request: Request):
    if not buy_sync_tracker.is_syncing:
        scheduler.modify_job("run_buyorder_sync", next_run_time=datetime.now())
        buy_sync_tracker.start()
    return templates.TemplateResponse(
        request=request,
        name="partials/sync_status.html",
        context={"tracker": buy_sync_tracker, "intent": Intent.buy},
    )


@router.post("/sellorder_states/refresh", response_class=HTMLResponse)
async def update_sellorder_states(request: Request):
    if not sell_sync_tracker.is_syncing:
        scheduler.modify_job("run_sellorder_sync", next_run_time=datetime.now())
        sell_sync_tracker.start()
    return templates.TemplateResponse(
        request=request,
        name="partials/sync_status.html",
        context={"tracker": sell_sync_tracker, "intent": Intent.sell},
    )


@router.get("/sync-status/{intent}", response_class=HTMLResponse)
async def sync_status(request: Request, intent: Intent):
    tracker = buy_sync_tracker if intent == Intent.buy else sell_sync_tracker
    return templates.TemplateResponse(
        request=request,
        name="partials/sync_status.html",
        context={"tracker": tracker, "intent": intent},
    )
