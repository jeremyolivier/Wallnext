from pydantic import BaseModel


class Thumbs(BaseModel):
    large: str
    original: str
    small: str


class Wallpaper(BaseModel):
    id: str
    url: str
    short_url: str
    views: int
    favorites: int
    source: str
    purity: str
    category: str
    dimension_x: int
    dimension_y: int
    resolution: str
    ratio: str
    file_size: int
    file_type: str
    created_at: str
    colors: list[str]
    path: str
    thumbs: Thumbs


class Meta(BaseModel):
    current_page: int
    last_page: int
    per_page: str
    total: int
    query: str
    seed: str | None = None


class SearchResult(BaseModel):
    data: list[Wallpaper]
    meta: Meta
