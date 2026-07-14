from datetime import datetime

from pydantic import BaseModel


class ItemResponse(BaseModel):
    id: int
    defindex: int
    name: str
    quality: str
    particle: str | None


class ListingResponse(BaseModel):
    id: str
    steamid: str
    intent: str
    status: str
    keys: int | None
    metal: float | None
    item_url: str
    item: ItemResponse

    model_config = {"from_attributes": True}


class BuyorderStateResponse(BaseModel):
    listing_id: str
    listing: ListingResponse
    steamid: str
    item_name: str
    user_keys: int | None
    user_metal: float | None
    top_competitor_keys: int | None
    top_competitor_metal: float | None
    outbid_by: str | None
    is_outbid: bool
    lowest_seller_keys: int | None
    lowest_seller_metal: float | None
    first_seen: datetime
    last_updated: datetime

    model_config = {"from_attributes": True}


class BuyorderStateHistoryResponse(BaseModel):
    id: int
    listing_id: str
    listing: ListingResponse
    changed_at: datetime
    old_user_keys: int | None
    old_user_metal: float | None
    old_top_competitor_keys: int | None
    old_top_competitor_metal: float | None
    old_is_outbid: bool
    old_lowest_seller_keys: int | None
    old_lowest_seller_metal: float | None

    new_user_keys: int | None
    new_user_metal: float | None
    new_top_competitor_keys: int | None
    new_top_competitor_metal: float | None
    new_is_outbid: bool
    new_lowest_seller_keys: int | None
    new_lowest_seller_metal: float | None

    outbid_changed: bool
    regained_top_changed: bool
    competitor_price_changed: bool
    price_updated_changed: bool
    lowest_seller_changed: bool
