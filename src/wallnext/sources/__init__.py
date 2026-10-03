import random
from pathlib import Path

from wallnext.config import Settings
from wallnext.exceptions import WallnextError
from wallnext.sources.apod.source import ApodSource
from wallnext.sources.base import Wallpaper, WallpaperSource
from wallnext.sources.wallhaven.source import WallhavenSource

__all__ = ["SOURCES", "Wallpaper", "WallpaperSource", "create", "identify"]

# Keyed like the [sources.<key>] tables of config.toml.
SOURCES: dict[str, type[WallpaperSource]] = {
    "wallhaven": WallhavenSource,
    "apod": ApodSource,
}


def _build(key: str, settings: Settings) -> WallpaperSource:
    match key:
        case "wallhaven":
            return WallhavenSource(**settings.sources.wallhaven.search_params())
        case "apod":
            return ApodSource(atleast=settings.sources.apod.atleast)
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
