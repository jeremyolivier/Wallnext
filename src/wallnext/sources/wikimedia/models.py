from pydantic import BaseModel


class ImageInfo(BaseModel):
    url: str
    width: int
    height: int
    mime: str


class Page(BaseModel):
    pageid: int
    title: str
    imageinfo: list[ImageInfo] = []


class Query(BaseModel):
    pages: list[Page] = []


class QueryResult(BaseModel):
    query: Query = Query()  # absent when the day has no picture
