from pydantic import BaseModel


class Entry(BaseModel):
    date: str  # YYYY-MM-DD
    title: str
    media_type: str  # "image", "video", …
    url: str  # the article page on science.nasa.gov
    hdurl: str | None = None  # the image, with its size in the w/h query parameters


class Page(BaseModel):
    entries: list[Entry]
    total_pages: int
