from typing import Optional
from urllib.parse import urlencode

from pydantic import BaseModel


class CurrencyValue(BaseModel):
    keys: Optional[float] = 0  # Float due to validation errors
    metal: Optional[float] = 0

    def __gt__(self, other: "CurrencyValue") -> bool:
        my_keys = self.keys or 0
        other_keys = other.keys or 0
        if my_keys != other_keys:
            return my_keys > other_keys
        return (self.metal or 0) > (other.metal or 0)


class ItemData(BaseModel):
    defindex: int
    name: str
    baseName: str
    quality: str
    particle: Optional[str] = None
    spells: list[str] = []


class BPListing(BaseModel):
    id: str
    steamid: str
    intent: str
    count: int
    status: str
    currencies: CurrencyValue
    details: Optional[str] = None
    item: ItemData
    item_url: str
    listedAt: int

    @classmethod
    def from_api(cls, data: dict) -> "BPListing":
        item = data.get("item", {})
        spells = [s["name"] for s in item.get("spells", [])]
        return cls(
            id=data["id"],
            steamid=data["steamid"],
            intent=data["intent"],
            count=data["count"],
            status=data["status"],
            currencies=CurrencyValue(**data.get("currencies", {})),
            details=data.get("details"),
            item=ItemData(
                defindex=item.get("defindex", ""),
                name=item.get("name", ""),
                baseName=item.get("baseName", ""),
                quality=item.get("quality", {}).get("name", ""),
                particle=item.get("particle", {}).get("name"),
                spells=spells,
            ),
            item_url=cls._build_classifieds_url(item),
            listedAt=data["listedAt"],
        )

    # TODO: make work on more item types
    @classmethod
    def _build_classifieds_url(cls, item: dict) -> str:
        params = {
            "item": item.get("baseName", ""),
            "quality": item.get("quality", {}).get("id", 6),
            "craftable": int(item.get("craftable", -1)),
        }

        particle = item.get("particle")
        if particle and particle.get("id"):
            params["particle"] = particle["id"]
        return "https://backpack.tf/classifieds?" + urlencode(params)


class SnapshotBPListing(BaseModel):
    steamid: str
    intent: str
    currencies: CurrencyValue
    details: Optional[str] = None
    isSpelled: bool
    itemName: str

    @classmethod
    def from_api(cls, data: dict, itemName: str) -> "SnapshotBPListing":
        return cls(
            steamid=data["steamid"],
            intent=data["intent"],
            currencies=CurrencyValue(**data.get("currencies", {})),
            details=data.get("details"),
            isSpelled=cls.has_spell(data["item"].get("attributes", [])),
            itemName=itemName,
        )

    @staticmethod
    def has_spell(attrs: list[dict]) -> bool:
        spell_defs = {"1004", "1005", "1006"}
        return any(str(a.get("defindex")) in spell_defs for a in attrs)


class BuyorderData(BaseModel):
    steamid: str
    outbid_by: str | None
    name: str
    users_price: CurrencyValue
    top_competitor_price: CurrencyValue
    outbid: bool
