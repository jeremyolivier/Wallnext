class WallnextError(Exception):
    """Base exception for wallnext."""


class SourceError(WallnextError):
    """A wallpaper source could not provide a wallpaper."""


class SourceAPIError(SourceError):
    """HTTP error returned by a source's API."""

    def __init__(self, source: str, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(f"{source} API error {status_code}: {message}")


class SourceNetworkError(SourceError):
    """Network or timeout error reaching a source's API."""


class WallpaperSetError(WallnextError):
    """Failed to apply wallpaper via Win32 API."""


class DownloadError(WallnextError):
    """Failed to download a wallpaper image."""
