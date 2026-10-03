from pydantic import BaseModel


class ItemData(BaseModel):
    nasa_id: str
    title: str


class Item(BaseModel):
    href: str  # the item's asset list (collection.json)
    data: list[ItemData]


class Metadata(BaseModel):
    total_hits: int


class Collection(BaseModel):
    items: list[Item]
    metadata: Metadata


class SearchResult(BaseModel):
    collection: Collection
