from datetime import datetime
from sqlalchemy import CheckConstraint, func, ForeignKey
from app.db.base import Base

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)


class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)


class Listing(Base):
    __tablename__ = "listings"
    id: Mapped[int] = mapped_column(primary_key=True)
    steamid: Mapped[int]
    intent: Mapped[str] = mapped_column(CheckConstraint("intent IN ('buy', 'sell')"))
    status: Mapped[str] = mapped_column(default="active")
    keys: Mapped[int | None] = mapped_column(default=0)
    metal: Mapped[float | None] = mapped_column(default=0.0)

    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"))
    item: Mapped["Item"] = relationship(back_populates="listings")


class Item(Base):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(primary_key=True)
    defindex: Mapped[int]
    name: Mapped[str]
    quality: Mapped[str]
    particle: Mapped[str | None]
    listings: Mapped[list["Listing"]] = relationship(back_populates="item")


class BuyorderState(Base):
    __tablename__ = "buyorder_states"
    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[str] = mapped_column(index=True)
    steamid: Mapped[int]
    item_name: Mapped[str]
    user_keys: Mapped[int | None] = mapped_column(default=0)
    user_metal: Mapped[float | None] = mapped_column(default=0.0)
    highest_keys: Mapped[int | None]
    highest_metal: Mapped[float | None]
    outbid_by: Mapped[str | None]
    is_outbid: Mapped[bool] = mapped_column(default=False)
    first_seen: Mapped[datetime] = mapped_column(server_default=func.now())
    last_updated: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
