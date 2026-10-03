"""Make wallnext.scr the Windows screensaver of the current user (no admin rights).

What the right-click "Install" on a .scr does: point HKCU\\Control Panel\\Desktop
at it, then apply the change with SystemParametersInfo.
"""

import sys
import winreg
from pathlib import Path

import win32api
import win32con
import win32gui

from wallnext.exceptions import WallnextError

_DESKTOP = r"Control Panel\Desktop"
_SCREENSAVER = "SCRNSAVE.EXE"
_APPLY = win32con.SPIF_UPDATEINIFILE | win32con.SPIF_SENDCHANGE


def scr_path() -> Path | None:
    """wallnext.scr next to the running exe; None when running from source."""
    path = Path(sys.executable).with_name("wallnext.scr")
    return path if path.exists() else None


def _registered() -> Path | None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _DESKTOP) as key:
            value, _ = winreg.QueryValueEx(key, _SCREENSAVER)
    except FileNotFoundError:
        return None
    if not value:
        return None
    try:
        return Path(win32api.GetLongPathName(value))
    except win32api.error:  # the registered file was deleted
        return Path(value)


def is_enabled() -> bool:
    """Whether Windows will start Wallnext's screensaver after the delay."""
    ours = scr_path()
    active = win32gui.SystemParametersInfo(win32con.SPI_GETSCREENSAVEACTIVE)
    registered = _registered()
    if not active or registered is None:
        return False
    if ours is not None:
        return registered.resolve() == ours.resolve()
    return registered.name.lower() == "wallnext.scr"


def timeout_minutes() -> int:
    seconds = win32gui.SystemParametersInfo(win32con.SPI_GETSCREENSAVETIMEOUT)
    return max(1, round(seconds / 60))


def enable(timeout: int) -> None:
    scr = scr_path()
    if scr is None:
        raise WallnextError("The screensaver is only available in the installed app.")
    # Short (8.3) path: older parts of Windows mishandle spaces in this value.
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, _DESKTOP, 0, winreg.KEY_SET_VALUE
    ) as key:
        winreg.SetValueEx(
            key, _SCREENSAVER, 0, winreg.REG_SZ, win32api.GetShortPathName(str(scr))
        )
    set_timeout(timeout)
    win32gui.SystemParametersInfo(win32con.SPI_SETSCREENSAVEACTIVE, 1, _APPLY)


def set_timeout(minutes: int) -> None:
    win32gui.SystemParametersInfo(
        win32con.SPI_SETSCREENSAVETIMEOUT, minutes * 60, _APPLY
    )


def disable() -> None:
    """Turn the screensaver off, if it is Wallnext's: never touch another one."""
    if not is_enabled():
        return
    win32gui.SystemParametersInfo(win32con.SPI_SETSCREENSAVEACTIVE, 0, _APPLY)
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, _DESKTOP, 0, winreg.KEY_SET_VALUE
    ) as key:
        winreg.DeleteValue(key, _SCREENSAVER)
