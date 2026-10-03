from wallnext.sources import http
from wallnext.sources.nasa_images.models import Collection, SearchResult

PAGE_SIZE = 100
MAX_PAGES = 100  # the API refuses pages past its first 10,000 results


class NasaImagesRequester:
    """The NASA Image and Video Library (images.nasa.gov). No API key needed."""

    def __init__(self):
        self.client = http.client("https://images-api.nasa.gov")

    def search(self, query: str, page: int = 1) -> Collection:
        resp = http.get(
            self.client,
            "NASA Images",
            "/search",
            params={
                "q": query,
                "media_type": "image",
                "page": page,
                "page_size": PAGE_SIZE,
            },
        )
        return SearchResult.model_validate(resp.json()).collection

    def assets(self, href: str) -> list[str]:
        """The files of one item: its sizes (~orig, ~large…) and metadata.json."""
        resp = http.get(self.client, "NASA Images", _https(href))
        return [_https(url) for url in resp.json()]

    def size(self, metadata_url: str) -> tuple[int, int] | None:
        """The original image's size, from its metadata.json."""
        metadata = http.get(self.client, "NASA Images", metadata_url).json()
        try:
            return int(metadata["File:ImageWidth"]), int(metadata["File:ImageHeight"])
        except KeyError, TypeError, ValueError:
            return None

    def close(self):
        self.client.close()


def _https(url: str) -> str:
    # Asset lists use plain http:// URLs; the same files are served over https.
    return url.replace("http://", "https://", 1)
