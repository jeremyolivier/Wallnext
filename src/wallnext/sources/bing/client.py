from wallnext.sources import http
from wallnext.sources.bing.models import Archive


class BingRequester:
    """Bing's picture of the day, from the endpoint behind bing.com's homepage.

    Undocumented but long-standing; it only serves the last 8 days.
    """

    def __init__(self):
        self.client = http.client("https://www.bing.com")

    def archive(self, market: str = "en-US") -> Archive:
        resp = http.get(
            self.client,
            "Bing",
            "/HPImageArchive.aspx",
            params={"format": "js", "idx": 0, "n": 8, "mkt": market},
        )
        return Archive.model_validate(resp.json())

    def close(self):
        self.client.close()
