import httpx

from wallnext.sources import http
from wallnext.sources.wallhaven.models import Collection, Collections, SearchResult


class WallhavenRequester:
    def __init__(self, api_key: str = ""):
        self.client = http.client("https://wallhaven.cc/api/v1")
        # Only sent for collections: searches stay free of the account's filters.
        self._key_header = {"X-API-Key": api_key} if api_key else {}

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

    def collections(self, username: str = "") -> list[Collection]:
        """The API key owner's collections, or `username`'s public ones."""
        path = f"/collections/{username}" if username else "/collections"
        resp = self._get(path, headers=self._key_header)
        return Collections.model_validate(resp.json()).data

    def collection(
        self, username: str, collection_id: int, purity: str = "100", page: int = 1
    ) -> SearchResult:
        """One page of the wallpapers in a collection (private ones need the key)."""
        resp = self._get(
            f"/collections/{username}/{collection_id}",
            params={"purity": purity, "page": page},
            headers=self._key_header,
        )
        return SearchResult.model_validate(resp.json())

    def random(self) -> SearchResult:
        return self.search(sorting="random")

    def toplist(self, toprange: str = "1M") -> SearchResult:
        return self.search(sorting="toplist", toprange=toprange)

    def close(self):
        self.client.close()
