import random
from pathlib import Path

from wallnext import credentials
from wallnext.config import Settings
from wallnext.exceptions import WallnextError
from wallnext.sources.apod.source import ApodSource
from wallnext.sources.base import Wallpaper, WallpaperSource
from wallnext.sources.bing.source import BingSource
from wallnext.sources.nasa_images.source import NasaImagesSource
from wallnext.sources.spotlight.source import SpotlightSource
from wallnext.sources.wallhaven.client import WallhavenRequester
from wallnext.sources.wallhaven.source import WallhavenSource
from wallnext.sources.wikimedia.source import WikimediaSource

__all__ = ["SOURCES", "Wallpaper", "WallpaperSource", "create", "identify"]

# Keyed like the [sources.<key>] tables of config.toml.
SOURCES: dict[str, type[WallpaperSource]] = {
    "wallhaven": WallhavenSource,
    "apod": ApodSource,
    "nasa_images": NasaImagesSource,
    "wikimedia": WikimediaSource,
    "bing": BingSource,
    "spotlight": SpotlightSource,
}


def _build(key: str, settings: Settings) -> WallpaperSource:
    match key:
        case "wallhaven":
            wallhaven = settings.sources.wallhaven
            if wallhaven.mode == "collection" and wallhaven.collection_id is not None:
                return WallhavenSource(
                    WallhavenRequester(credentials.get("wallhaven")),
                    collection=(wallhaven.username, wallhaven.collection_id),
                    purity=wallhaven.purity,
                )
            return WallhavenSource(**wallhaven.search_params())
        case "apod":
            return ApodSource(atleast=settings.sources.apod.atleast)
        case "nasa_images":
            nasa = settings.sources.nasa_images
            return NasaImagesSource(query=nasa.query, atleast=nasa.atleast)
        case "wikimedia":
            return WikimediaSource(atleast=settings.sources.wikimedia.atleast)
        case "bing":
            return BingSource()
        case "spotlight":
            return SpotlightSource()
    raise ValueError(f"Unknown source: {key}")


def create(settings: Settings) -> WallpaperSource:
    """One of the enabled sources, picked at random."""
    enabled = [key for key in SOURCES if settings.source(key).enabled]
    if not enabled:
        raise WallnextError("No source enabled — enable one in the settings window.")
    return _build(random.choice(enabled), settings)


def identify(wallpaper: Path) -> tuple[type[WallpaperSource], str] | None:
    """The source a downloaded wallpaper came from and its web page, if known."""
    for source in SOURCES.values():
        if url := source.page_url(wallpaper):
            return source, url
    return None
