import random
import re
from pathlib import Path
from typing import Any, ClassVar

from wallnext.sources.base import Wallpaper
from wallnext.sources.wallhaven.client import WallhavenRequester


class WallhavenSource:
    name: ClassVar[str] = "Wallhaven"

    def __init__(
        self,
        requester: WallhavenRequester | None = None,
        **search_params: Any,
    ) -> None:
        self._requester = requester or WallhavenRequester()
        # Empty params -> default top list; otherwise drive the search endpoint.
        self._search_params = {k: v for k, v in search_params.items() if v != ""}

    def random_wallpaper(self) -> Wallpaper:
        if self._search_params:
            result = self._requester.search(**self._search_params)
        else:
            result = self._requester.toplist()
        url = random.choice(result.data).path
        # Keep Wallhaven's file name, wallhaven-<id>.<ext>: page_url relies on it.
        return Wallpaper(url=url, filename=url.rsplit("/", 1)[-1])

    @staticmethod
    def page_url(wallpaper: Path) -> str | None:
        match = re.fullmatch(r"wallhaven-(\w+)", wallpaper.stem)
        return f"https://wallhaven.cc/w/{match[1]}" if match else None
