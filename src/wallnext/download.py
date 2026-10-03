from pathlib import Path

import httpx

from wallnext.exceptions import DownloadError
from wallnext.sources.http import USER_AGENT


def download(url: str, dest: Path) -> Path:
    """Stream `url` to `dest`, creating its directory as needed."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with httpx.stream(
            "GET",
            url,
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as resp:
            resp.raise_for_status()
            with open(dest, "wb") as f:
                f.writelines(resp.iter_bytes())
    except httpx.HTTPStatusError as e:
        raise DownloadError(f"HTTP {e.response.status_code} for {url}") from e
    except httpx.TimeoutException as e:
        raise DownloadError("Download timed out.") from e
    except httpx.RequestError as e:
        raise DownloadError(f"Network error: {e}") from e
    return dest
