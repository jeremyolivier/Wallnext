import random
import re
from pathlib import Path, PurePosixPath
from typing import ClassVar
from urllib.parse import parse_qs, urlsplit

from wallnext.exceptions import ApodError
from wallnext.sources.apod.client import ApodRequester
from wallnext.sources.apod.models import Entry
from wallnext.sources.base import Wallpaper

_PER_PAGE = 100  # the API's maximum: fewer requests to find a large picture
_ATTEMPTS = 5


def _size(entry: Entry) -> tuple[int, int] | None:
    """The image size, read from hdurl's w/h query parameters."""
    if not entry.hdurl:
        return None
    query = parse_qs(urlsplit(entry.hdurl).query)
    try:
        return int(query["w"][0]), int(query["h"][0])
    except KeyError, ValueError:
        return None


def _original(url: str) -> str:
    """The original file behind a resized "dynamicimage" URL.

    Recent hdurls go through an image resizer that recompresses the picture,
    even at full size; the same path under /content/dam/ serves the original.
    """
    parts = urlsplit(url)
    path = parts.path.replace("/dynamicimage/assets/", "/content/dam/", 1)
    return parts._replace(path=path, query="").geturl()


def _parse_resolution(value: str) -> tuple[int, int]:
    """Parse "2560x1440" into (2560, 1440); empty or malformed means no minimum."""
    match = re.fullmatch(r"(\d+)x(\d+)", value.strip())
    return (int(match[1]), int(match[2])) if match else (0, 0)


class ApodSource:
    name: ClassVar[str] = "NASA APOD"

    def __init__(
        self, requester: ApodRequester | None = None, atleast: str = ""
    ) -> None:
        self._requester = requester or ApodRequester()
        self._min_width, self._min_height = _parse_resolution(atleast)

    def _fits(self, entry: Entry) -> bool:
        """A landscape image of at least the minimum resolution.

        APOD also has videos, portrait pictures and many small old images.
        """
        if entry.media_type != "image" or (size := _size(entry)) is None:
            return False
        width, height = size
        return (
            width > height and width >= self._min_width and height >= self._min_height
        )

    def random_wallpaper(self) -> Wallpaper:
        # The API has no random order: pick a random page of the archive.
        total_pages = self._requester.entries(per_page=_PER_PAGE).total_pages
        for _ in range(_ATTEMPTS):
            page = self._requester.entries(
                page=random.randint(1, total_pages), per_page=_PER_PAGE
            )
            candidates = [entry for entry in page.entries if self._fits(entry)]
            if candidates:
                entry = random.choice(candidates)
                assert entry.hdurl  # checked by _fits
                url = _original(entry.hdurl)
                suffix = PurePosixPath(urlsplit(url).path).suffix
                return Wallpaper(url=url, filename=f"apod-{entry.date}{suffix}")
        raise ApodError(
            "No picture large enough found, try again or lower the minimum resolution."
        )

    @staticmethod
    def page_url(wallpaper: Path) -> str | None:
        # Downloads are named apod-YYYY-MM-DD.<ext>; apod.nasa.gov pages apYYMMDD.html.
        match = re.fullmatch(r"apod-\d\d(\d\d)-(\d\d)-(\d\d)", wallpaper.stem)
        return (
            f"https://apod.nasa.gov/apod/ap{''.join(match.groups())}.html"
            if match
            else None
        )
