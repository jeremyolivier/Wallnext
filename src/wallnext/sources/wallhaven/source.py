import random
import re
from pathlib import Path
from typing import Any

from wallnext.sources.wallhaven.client import WallhavenRequester


class WallhavenSource:
    def __init__(
        self,
        requester: WallhavenRequester | None = None,
        **search_params: Any,
    ) -> None:
        self._requester = requester or WallhavenRequester()
        # Empty params -> default top list; otherwise drive the search endpoint.
        self._search_params = {k: v for k, v in search_params.items() if v != ""}

    def random_url(self) -> str:
        if self._search_params:
            result = self._requester.search(**self._search_params)
        else:
            result = self._requester.toplist()
        return random.choice(result.data).path


def page_url(wallpaper: Path) -> str | None:
    """The wallhaven.cc page of a downloaded wallpaper, if it came from Wallhaven."""
    # Downloads keep Wallhaven's file name: wallhaven-<id>.<ext>.
    match = re.fullmatch(r"wallhaven-(\w+)", wallpaper.stem)
    return f"https://wallhaven.cc/w/{match[1]}" if match else None
