import random
import re
from datetime import date, timedelta
from pathlib import Path, PurePosixPath
from typing import ClassVar
from urllib.parse import urlsplit

from wallnext.exceptions import SourceError
from wallnext.sources import http
from wallnext.sources.base import Wallpaper
from wallnext.sources.wikimedia.client import WikimediaRequester
from wallnext.sources.wikimedia.models import ImageInfo

# Pictures of the day are reliably archived from 2007 on.
_FIRST_DAY = date(2007, 1, 1)
_ATTEMPTS = 8
_FORMATS = {"image/jpeg", "image/png"}


class WikimediaSource:
    name: ClassVar[str] = "Wikimedia Commons"

    def __init__(
        self, requester: WikimediaRequester | None = None, atleast: str = ""
    ) -> None:
        self._requester = requester or WikimediaRequester()
        self._atleast = atleast

    def _fits(self, info: ImageInfo) -> bool:
        return info.mime in _FORMATS and http.fits(
            info.width, info.height, self._atleast
        )

    def random_wallpaper(self) -> Wallpaper:
        span = (date.today() - _FIRST_DAY).days  # noqa: DTZ011 — a local calendar day
        for _ in range(_ATTEMPTS):
            day = _FIRST_DAY + timedelta(days=random.randint(0, span))
            for page in self._requester.picture_of_the_day(day):
                info = next((i for i in page.imageinfo if self._fits(i)), None)
                if info:
                    url = urlsplit(info.url)._replace(query="").geturl()
                    suffix = PurePosixPath(urlsplit(url).path).suffix
                    return Wallpaper(
                        url=url, filename=f"wikimedia-{page.pageid}{suffix}"
                    )
        raise SourceError(
            "Wikimedia Commons: no picture large enough found, try again or lower "
            "the minimum resolution."
        )

    @staticmethod
    def page_url(wallpaper: Path) -> str | None:
        match = re.fullmatch(r"wikimedia-(\d+)", wallpaper.stem)
        return (
            f"https://commons.wikimedia.org/w/index.php?curid={match[1]}"
            if match
            else None
        )
