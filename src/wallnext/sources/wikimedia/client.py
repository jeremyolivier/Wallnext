from datetime import date

from wallnext.sources import http
from wallnext.sources.wikimedia.models import Page, QueryResult


class WikimediaRequester:
    """Wikimedia Commons, through the MediaWiki API. No API key needed."""

    def __init__(self):
        self.client = http.client("https://commons.wikimedia.org/w")

    def picture_of_the_day(self, day: date) -> list[Page]:
        """The file(s) shown as Commons' picture of the day on `day`."""
        resp = http.get(
            self.client,
            "Wikimedia Commons",
            "/api.php",
            params={
                "action": "query",
                "format": "json",
                "formatversion": 2,
                "generator": "images",
                "titles": f"Template:Potd/{day:%Y-%m-%d}",
                "prop": "imageinfo",
                "iiprop": "url|size|mime",
            },
        )
        return QueryResult.model_validate(resp.json()).query.pages

    def close(self):
        self.client.close()
