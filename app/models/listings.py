from urllib.parse import urlencode

from pydantic import BaseModel


class CurrencyValue(BaseModel):
    keys: float | None = 0  # Float due to validation errors
    metal: float | None = 0

    def __gt__(self, other: CurrencyValue) -> bool:
        my_keys = self.keys or 0
        other_keys = other.keys or 0
        if my_keys != other_keys:
            return my_keys > other_keys
        return (self.metal or 0) > (other.metal or 0)

    def __ge__(self, other: CurrencyValue) -> bool:
        return self == other or self > other


class ItemData(BaseModel):
    defindex: int | None
    name: str
    base_name: str
    quality: str
    particle: str | None = None
    spells: list[str] = []


class BPListing(BaseModel):
    id: str
    steamid: str
    intent: str
    count: int
    status: str
    currencies: CurrencyValue
    details: str | None = None
    item: ItemData
    item_url: str
    listed_at: int

    @classmethod
    def from_api(cls, data: dict) -> BPListing:
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
                defindex=item.get("defindex", None),
                name=item.get("name", ""),
                base_name=item.get("baseName", ""),
                quality=item.get("quality", {}).get("name", ""),
                particle=item.get("particle", {}).get("name"),
                spells=spells,
            ),
            item_url=cls._build_classifieds_url(item),
            listed_at=data["listedAt"],
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
    details: str | None = None
    is_spelled: bool
    item_name: str

    @classmethod
    def from_api(cls, data: dict, item_name: str) -> SnapshotBPListing:
        return cls(
            steamid=data["steamid"],
            intent=data["intent"],
            currencies=CurrencyValue(**data.get("currencies", {})),
            details=data.get("details"),
            is_spelled=cls.has_spell(data["item"].get("attributes", [])),
            item_name=item_name,
        )

    @staticmethod
    def has_spell(attrs: list[dict]) -> bool:
        spell_defs = {"1004", "1005", "1006"}
        return any(str(a.get("defindex")) in spell_defs for a in attrs)
