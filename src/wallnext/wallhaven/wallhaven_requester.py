import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

from wallnext.exceptions import WallhavenAPIError, WallhavenNetworkError
from wallnext.wallhaven.models import SearchResult

load_dotenv()


class WallhavenRequester:
    def __init__(self):
        self.api_key = os.getenv("WALLHAVEN_API_KEY")
        self.client = httpx.Client(
            base_url="https://wallhaven.cc/api/v1",
            params={"apikey": self.api_key} if self.api_key else {},
            timeout=10,
        )

    def _get(self, *args, **kwargs) -> httpx.Response:
        try:
            resp = self.client.get(*args, **kwargs)
            resp.raise_for_status()
            return resp
        except httpx.HTTPStatusError as e:
            raise WallhavenAPIError(e.response.status_code, e.response.text) from e
        except httpx.TimeoutException as e:
            raise WallhavenNetworkError("Request timed out.") from e
        except httpx.RequestError as e:
            raise WallhavenNetworkError(f"Network error: {e}") from e

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

    def download(self, url: str, dest_dir: Path, filename: str | None = None) -> Path:
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / (filename or url.split("/")[-1])
        try:
            with self.client.stream("GET", url) as resp:
                resp.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in resp.iter_bytes():
                        f.write(chunk)
        except httpx.HTTPStatusError as e:
            raise WallhavenAPIError(e.response.status_code, e.response.text) from e
        except httpx.TimeoutException as e:
            raise WallhavenNetworkError("Download timed out.") from e
        except httpx.RequestError as e:
            raise WallhavenNetworkError(f"Network error: {e}") from e
        return dest

    def close(self):
        self.client.close()
