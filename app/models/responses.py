from pydantic import BaseModel
from datetime import datetime


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
