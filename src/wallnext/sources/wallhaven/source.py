import random
import re
from pathlib import Path
from typing import Any, ClassVar

from wallnext.exceptions import SourceError
from wallnext.sources.base import Wallpaper
from wallnext.sources.wallhaven.client import WallhavenRequester
from wallnext.sources.wallhaven.models import SearchResult


def _searches(query: str) -> list[str]:
    """Comma-separated searches; one is picked per wallpaper.

    Done here because Wallhaven's "a | b" only works with single words.
    """
    return [search.strip() for search in query.split(",") if search.strip()] or [""]


# Sorted listings beyond the top 240 wallpapers stop meaning "most viewed" etc.
_MAX_PAGES = 10


class WallhavenSource:
    name: ClassVar[str] = "Wallhaven"

    def __init__(
        self,
        requester: WallhavenRequester | None = None,
        collection: tuple[str, int] | None = None,
        **search_params: Any,
    ) -> None:
        """Search Wallhaven, or pick from `collection` (username, collection id)."""
        self._requester = requester or WallhavenRequester()
        self._collection = collection
        self._search_params = {k: v for k, v in search_params.items() if v != ""}

    def random_wallpaper(self) -> Wallpaper:
        result = self._collection_page() if self._collection else self._search_page()
        if not result.data:
            raise SourceError("Wallhaven: no wallpaper matches these settings.")
        url = random.choice(result.data).path
        # Keep Wallhaven's file name, wallhaven-<id>.<ext>: page_url relies on it.
        return Wallpaper(url=url, filename=url.rsplit("/", 1)[-1])

    def _search_page(self) -> SearchResult:
        """A random page of the search, not always the first 24 results."""
        params = dict(self._search_params) or {"sorting": "toplist"}
        if "query" in params:
            params["query"] = random.choice(_searches(params["query"]))
        first = self._requester.search(**params)
        # A toplist is already bounded by its period: all of it is "top".
        last = first.meta.last_page
        pages = last if params.get("sorting") == "toplist" else min(last, _MAX_PAGES)
        page = random.randint(1, max(pages, 1))
        return first if page == 1 else self._requester.search(**params, page=page)

    def _collection_page(self) -> SearchResult:
        assert self._collection
        username, collection_id = self._collection
        purity = self._search_params.get("purity", "100")
        first = self._requester.collection(username, collection_id, purity)
        page = random.randint(1, max(first.meta.last_page, 1))
        if page == 1:
            return first
        return self._requester.collection(username, collection_id, purity, page)

    @staticmethod
    def page_url(wallpaper: Path) -> str | None:
        match = re.fullmatch(r"wallhaven-(\w+)", wallpaper.stem)
        return f"https://wallhaven.cc/w/{match[1]}" if match else None
