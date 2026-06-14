from pydantic import BaseModel
from typing import Optional


class CurrencyValue(BaseModel):
    keys: Optional[int] = 0
    metal: Optional[float] = 0

    def __gt__(self, other: "CurrencyValue") -> bool:
        my_keys = self.keys or 0
        other_keys = other.keys or 0
        if my_keys != other_keys:
            return my_keys > other_keys
        return (self.metal or 0) > (other.metal or 0)


class Item(BaseModel):
    name: str
    baseName: str
    quality: str
    particle: Optional[str] = None
    spells: list[str] = []


class Listing(BaseModel):
    id: str
    steamid: str
    intent: str
    count: int
    status: str
    currencies: CurrencyValue
    details: Optional[str] = None
    item: Item
    listedAt: int

    @classmethod
    def from_api(cls, data: dict) -> "Listing":
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
            item=Item(
                name=item.get("name", ""),
                baseName=item.get("baseName", ""),
                quality=item.get("quality", {}).get("name", ""),
                particle=item.get("particle", {}).get("name"),
                spells=spells,
            ),
            listedAt=data["listedAt"],
        )


class ItemListing(BaseModel):
    steamid: str
    intent: str
    currencies: CurrencyValue
    details: Optional[str] = None
    isSpelled: bool
    itemName: str

    @classmethod
    def from_api(cls, data: dict, itemName: str) -> "Listing":
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
