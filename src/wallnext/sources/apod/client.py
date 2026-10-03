import httpx

from wallnext.exceptions import ApodAPIError, ApodNetworkError
from wallnext.sources.apod.models import Entry, Page


class ApodRequester:
    """NASA's Astronomy Picture of the Day, from the science.nasa.gov WordPress API.

    Replaces the api.nasa.gov APOD API, archived on 2026-12-01. No API key needed.
    """

    def __init__(self):
        self.client = httpx.Client(
            base_url="https://science.nasa.gov/wp-json/wp/v2",
            timeout=10,
        )

    def entries(self, page: int = 1, per_page: int = 20) -> Page:
        """One page of entries, newest first (per_page is capped at 100)."""
        try:
            resp = self.client.get(
                "/apod-basic", params={"page": page, "per_page": per_page}
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise ApodAPIError(e.response.status_code, e.response.text) from e
        except httpx.TimeoutException as e:
            raise ApodNetworkError("Request timed out.") from e
        except httpx.RequestError as e:
            raise ApodNetworkError(f"Network error: {e}") from e
        return Page(
            entries=[Entry.model_validate(entry) for entry in resp.json()],
            total_pages=int(resp.headers.get("X-WP-TotalPages", 1)),
        )

    def close(self):
        self.client.close()
