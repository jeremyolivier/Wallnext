import math
import random
import re
from pathlib import Path, PurePosixPath
from typing import ClassVar
from urllib.parse import quote, urlsplit

from wallnext.exceptions import SourceError
from wallnext.sources import http
from wallnext.sources.base import Wallpaper
from wallnext.sources.nasa_images.client import (
    MAX_PAGES,
    PAGE_SIZE,
    NasaImagesRequester,
)
from wallnext.sources.nasa_images.models import Item

# Each candidate costs two requests (asset list + metadata).
_CANDIDATES = 8


class NasaImagesSource:
    name: ClassVar[str] = "NASA Images"

    def __init__(
        self,
        requester: NasaImagesRequester | None = None,
        query: str = "galaxy",
        atleast: str = "",
    ) -> None:
        self._requester = requester or NasaImagesRequester()
        self._query = query
        self._atleast = atleast

    def random_wallpaper(self) -> Wallpaper:
        first = self._requester.search(self._query)
        if not first.items:
            raise SourceError(f"NASA Images: nothing matches “{self._query}”.")
        pages = min(math.ceil(first.metadata.total_hits / PAGE_SIZE), MAX_PAGES)
        page = random.randint(1, pages)
        items = (
            first.items
            if page == 1
            else self._requester.search(self._query, page).items
        )
        for item in random.sample(items, min(_CANDIDATES, len(items))):
            if wallpaper := self._wallpaper(item):
                return wallpaper
        raise SourceError(
            "NASA Images: no picture large enough found, try again or lower the "
            "minimum resolution."
        )

    def _wallpaper(self, item: Item) -> Wallpaper | None:
        assets = self._requester.assets(item.href)
        original = next((url for url in assets if "~orig." in url), None)
        metadata = next((url for url in assets if url.endswith("/metadata.json")), None)
        if not original or not metadata:
            return None
        size = self._requester.size(metadata)
        if size is None or not http.fits(*size, self._atleast):
            return None
        suffix = PurePosixPath(urlsplit(original).path).suffix
        # The id ends up in a file name: escape anything a path cannot hold.
        nasa_id = quote(item.data[0].nasa_id, safe="")
        return Wallpaper(url=original, filename=f"nasa-{nasa_id}{suffix}")

    @staticmethod
    def page_url(wallpaper: Path) -> str | None:
        match = re.fullmatch(r"nasa-(.+)", wallpaper.stem)
        return f"https://images.nasa.gov/details/{match[1]}" if match else None
