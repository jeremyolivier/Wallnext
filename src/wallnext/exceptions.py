class WallnextError(Exception):
    """Base exception for wallnext."""


class WallhavenAPIError(WallnextError):
    """HTTP error returned by Wallhaven API."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(f"Wallhaven API error {status_code}: {message}")


class WallhavenNetworkError(WallnextError):
    """Network or timeout error reaching Wallhaven."""


class WallpaperSetError(WallnextError):
    """Failed to apply wallpaper via Win32 API."""
