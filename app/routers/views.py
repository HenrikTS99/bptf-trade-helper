from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import get_stored_buyorder_states
from app.db.base import get_db

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def display_dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    beaten_buyorders = await get_stored_buyorder_states(db, only_beaten=False)
    return templates.TemplateResponse(
        request=request,
        name="pages/dashboard.html",
        context={"beaten_buyorders": beaten_buyorders},
    )
