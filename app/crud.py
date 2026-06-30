from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db import models


async def get_stored_listings(
    db: AsyncSession, intent: str | None = None
) -> list[models.Listing]:
    stmt = select(models.Listing).options(joinedload(models.Listing.item))
    if intent:
        stmt = stmt.where(models.Listing.intent == intent)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_stored_buyorder_states(
    db: AsyncSession, only_beaten: bool = False
) -> list[models.BuyorderState]:
    stmt = select(models.BuyorderState).options(
        joinedload(models.BuyorderState.listing).joinedload(models.Listing.item)
    )
    if only_beaten:
        stmt = stmt.where(models.BuyorderState.is_outbid == only_beaten)
    result = await db.execute(stmt)
    return result.scalars().all()
