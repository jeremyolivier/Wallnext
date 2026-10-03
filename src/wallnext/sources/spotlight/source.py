import random
from pathlib import Path, PurePosixPath
from typing import ClassVar
from urllib.parse import urlsplit

from wallnext.exceptions import SourceError
from wallnext.sources.base import Wallpaper
from wallnext.sources.spotlight.client import SpotlightRequester

_ASSETS = "https://res.public.onecdn.static.microsoft/creativeservice/"


class SpotlightSource:
    name: ClassVar[str] = "Windows Spotlight"

    def __init__(self, requester: SpotlightRequester | None = None) -> None:
        self._requester = requester or SpotlightRequester()

    def random_wallpaper(self) -> Wallpaper:
        ads = self._requester.selection()
        if not ads:
            raise SourceError("Windows Spotlight returned no picture.")
        url = random.choice(ads).landscapeImage.asset
        return Wallpaper(
            url=url, filename=f"spotlight-{PurePosixPath(urlsplit(url).path).name}"
        )

    @staticmethod
    def page_url(wallpaper: Path) -> str | None:
        # Spotlight has no page per picture: link to the full-size image.
        name = wallpaper.name.removeprefix("spotlight-")
        return f"{_ASSETS}{name}" if name != wallpaper.name else None
