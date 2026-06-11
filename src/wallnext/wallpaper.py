import ctypes.wintypes
from pathlib import Path
from typing import Final

from wallnext.exceptions import WallpaperSetError

SPI_SETDESKWALLPAPER: Final[int] = 0x0014
SPIF_UPDATEINIFILE: Final[int] = 0x01
SPIF_SENDCHANGE: Final[int] = 0x02

_user32 = ctypes.WinDLL("user32")
_user32.SystemParametersInfoW.argtypes = [
    ctypes.wintypes.UINT,
    ctypes.wintypes.UINT,
    ctypes.wintypes.LPCWSTR,
    ctypes.wintypes.UINT,
]
_user32.SystemParametersInfoW.restype = ctypes.wintypes.BOOL


def set_wallpaper(path: Path) -> None:
    ok = _user32.SystemParametersInfoW(
        SPI_SETDESKWALLPAPER,
        0,
        str(path.resolve()),
        SPIF_UPDATEINIFILE | SPIF_SENDCHANGE,
    )
    if not ok:
        raise WallpaperSetError(f"SystemParametersInfoW failed for {path}")
