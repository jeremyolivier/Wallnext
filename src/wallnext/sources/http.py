"""HTTP plumbing shared by the source clients."""

import re
from typing import Any

import httpx2

from wallnext.exceptions import SourceAPIError, SourceNetworkError

# Some APIs (Wikimedia) reject generic user agents such as httpx2's default.
USER_AGENT = "wallnext/0.1 (+https://github.com/jeremyolivier/wallnext)"


def client(base_url: str = "") -> httpx2.Client:
    return httpx2.Client(
        base_url=base_url, timeout=10, headers={"User-Agent": USER_AGENT}
    )


def get(client: httpx2.Client, source: str, url: str, **kwargs: Any) -> httpx2.Response:
    """GET `url`, turning HTTP and network failures into source errors."""
    try:
        resp = client.get(url, **kwargs)
        resp.raise_for_status()
    except httpx2.HTTPStatusError as e:
        raise SourceAPIError(source, e.response.status_code, e.response.text) from e
    except httpx2.TimeoutException as e:
        raise SourceNetworkError(f"{source}: request timed out.") from e
    except httpx2.RequestError as e:
        raise SourceNetworkError(f"{source}: network error: {e}") from e
    return resp


def parse_resolution(value: str) -> tuple[int, int]:
    """Parse "2560x1440" into (2560, 1440); empty or malformed means no minimum."""
    match = re.fullmatch(r"(\d+)x(\d+)", value.strip())
    return (int(match[1]), int(match[2])) if match else (0, 0)


def fits(width: int, height: int, atleast: str) -> bool:
    """A landscape picture of at least the `atleast` resolution."""
    min_width, min_height = parse_resolution(atleast)
    return width > height and width >= min_width and height >= min_height
