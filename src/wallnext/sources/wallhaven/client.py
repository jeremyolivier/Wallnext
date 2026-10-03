import httpx

from wallnext.sources import http
from wallnext.sources.wallhaven.models import SearchResult


class WallhavenRequester:
    def __init__(self):
        self.client = http.client("https://wallhaven.cc/api/v1")

    def _get(self, *args, **kwargs) -> httpx.Response:
        return http.get(self.client, "Wallhaven", *args, **kwargs)

    def search(
        self,
        query: str = "",
        categories: str = "101",
        purity: str = "100",
        sorting: str = "date_added",
        order: str = "desc",
        toprange: str = "1M",
        atleast: str = "",
        resolutions: str = "",
        ratios: str = "",
        colors: str = "",
        page: int = 1,
        seed: str = "",
    ) -> SearchResult:
        params = {
            k: v
            for k, v in {
                "q": query,
                "categories": categories,
                "purity": purity,
                "sorting": sorting,
                "order": order,
                "page": page,
                "topRange": toprange if sorting == "toplist" else None,
                "atleast": atleast or None,
                "resolutions": resolutions or None,
                "ratios": ratios or None,
                "colors": colors or None,
                "seed": seed or None,
            }.items()
            if v is not None
        }

        return SearchResult.model_validate(self._get("/search", params=params).json())

    def random(self) -> SearchResult:
        return self.search(sorting="random")

    def toplist(self, toprange: str = "1M") -> SearchResult:
        return self.search(sorting="toplist", toprange=toprange)

    def close(self):
        self.client.close()
