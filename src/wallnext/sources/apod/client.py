from wallnext.sources import http
from wallnext.sources.apod.models import Entry, Page


class ApodRequester:
    """NASA's Astronomy Picture of the Day, from the science.nasa.gov WordPress API.

    Replaces the api.nasa.gov APOD API, archived on 2026-12-01. No API key needed.
    """

    def __init__(self):
        self.client = http.client("https://science.nasa.gov/wp-json/wp/v2")

    def entries(self, page: int = 1, per_page: int = 20) -> Page:
        """One page of entries, newest first (per_page is capped at 100)."""
        resp = http.get(
            self.client,
            "NASA APOD",
            "/apod-basic",
            params={"page": page, "per_page": per_page},
        )
        return Page(
            entries=[Entry.model_validate(entry) for entry in resp.json()],
            total_pages=int(resp.headers.get("X-WP-TotalPages", 1)),
        )

    def close(self):
        self.client.close()
