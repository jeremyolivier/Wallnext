from wallnext.sources import http
from wallnext.sources.spotlight.models import Ad, Selection

# Windows Spotlight's desktop placement, as requested by Windows itself.
_DESKTOP_PLACEMENT = "88000820"


class SpotlightRequester:
    """Windows Spotlight pictures, from the API Windows uses for the desktop.

    Undocumented: it may change without notice.
    """

    def __init__(self):
        self.client = http.client("https://fd.api.iris.microsoft.com/v4/api")

    def selection(self, count: int = 4, locale: str = "en-US") -> list[Ad]:
        resp = http.get(
            self.client,
            "Windows Spotlight",
            "/selection",
            params={
                "placement": _DESKTOP_PLACEMENT,
                "bcnt": count,
                "country": locale.rsplit("-", 1)[-1],
                "locale": locale,
                "fmt": "json",
            },
        )
        selection = Selection.model_validate(resp.json())
        return [batch.item.ad for batch in selection.batchrsp.items]

    def close(self):
        self.client.close()
