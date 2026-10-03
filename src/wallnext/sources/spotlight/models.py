from pydantic import BaseModel, Json


class Asset(BaseModel):
    asset: str  # image URL


class Ad(BaseModel):
    title: str
    landscapeImage: Asset


class Item(BaseModel):
    ad: Ad


class BatchItem(BaseModel):
    item: Json[Item]  # the API nests each item as a JSON string


class BatchResponse(BaseModel):
    items: list[BatchItem]


class Selection(BaseModel):
    batchrsp: BatchResponse
