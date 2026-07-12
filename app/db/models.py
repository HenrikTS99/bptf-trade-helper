from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.base import Base


class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)


class Listing(Base):
    __tablename__ = "listings"
    id: Mapped[str] = mapped_column(primary_key=True)
    steamid: Mapped[str]
    intent: Mapped[str] = mapped_column(CheckConstraint("intent IN ('buy', 'sell')"))
    status: Mapped[str] = mapped_column(default="active")
    keys: Mapped[int | None] = mapped_column(default=0)
    metal: Mapped[float | None] = mapped_column(default=0.0)

    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"))
    item_url: Mapped[str]
    item: Mapped["Item"] = relationship(back_populates="listings")

    buyorder_states: Mapped[list["BuyorderState"]] = relationship(
        back_populates="listing"
    )
    buyorder_state_history: Mapped[list["BuyorderStateHistory"]] = relationship(
        back_populates="listing"
    )


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (UniqueConstraint("name", "quality", "particle", name="uq_item"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    defindex: Mapped[int]
    name: Mapped[str]
    quality: Mapped[str]
    particle: Mapped[str | None]
    listings: Mapped[list["Listing"]] = relationship(back_populates="item")


class BuyorderState(Base):
    __tablename__ = "buyorder_states"
    listing_id: Mapped[str] = mapped_column(ForeignKey("listings.id"), primary_key=True)
    listing: Mapped["Listing"] = relationship(back_populates="buyorder_states")
    steamid: Mapped[str]
    item_name: Mapped[str]
    user_keys: Mapped[int | None] = mapped_column(default=0)
    user_metal: Mapped[float | None] = mapped_column(default=0.0)
    top_competitor_keys: Mapped[int | None]
    top_competitor_metal: Mapped[float | None]
    outbid_by: Mapped[str | None]
    is_outbid: Mapped[bool] = mapped_column(default=False)
    lowest_seller_keys: Mapped[int | None]
    lowest_seller_metal: Mapped[float | None]
    first_seen: Mapped[datetime] = mapped_column(server_default=func.now())
    last_updated: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    def is_same_as(self, other: "BuyorderState") -> bool:
        return (
            self.user_keys == other.user_keys
            and self.user_metal == other.user_metal
            and self.top_competitor_keys == other.top_competitor_keys
            and self.top_competitor_metal == other.top_competitor_metal
            and self.is_outbid == other.is_outbid
            and self.lowest_seller_keys == other.lowest_seller_keys
            and self.lowest_seller_metal == other.lowest_seller_metal
        )


class BuyorderStateHistory(Base):
    __tablename__ = "buyorder_state_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[str] = mapped_column(ForeignKey("listings.id"))
    listing: Mapped["Listing"] = relationship(back_populates="buyorder_state_history")
    changed_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
    # old states
    old_user_keys: Mapped[int | None]
    old_user_metal: Mapped[float | None]
    old_top_competitor_keys: Mapped[int | None]
    old_top_competitor_metal: Mapped[float | None]
    old_is_outbid: Mapped[bool] = mapped_column(default=False)
    old_lowest_seller_keys: Mapped[int | None]
    old_lowest_seller_metal: Mapped[float | None]
    # new states
    new_user_keys: Mapped[int | None]
    new_user_metal: Mapped[float | None]
    new_top_competitor_keys: Mapped[int | None]
    new_top_competitor_metal: Mapped[float | None]
    new_is_outbid: Mapped[bool] = mapped_column(default=False)
    new_lowest_seller_keys: Mapped[int | None]
    new_lowest_seller_metal: Mapped[float | None]
    # change types
    outbid_changed: Mapped[bool] = mapped_column(default=False)
    regained_top_changed: Mapped[bool] = mapped_column(default=False)
    competitor_price_changed: Mapped[bool] = mapped_column(default=False)
    price_updated_changed: Mapped[bool] = mapped_column(default=False)
    lowest_seller_changed: Mapped[bool] = mapped_column(default=False)
