from collections.abc import Iterator

import pywintypes
import win32api
import win32con


def _resolutions() -> Iterator[tuple[int, int]]:
    # Display modes are physical pixels, unaffected by Windows display scaling.
    index = 0
    while True:
        try:
            device = win32api.EnumDisplayDevices(None, index)
        except pywintypes.error:
            return
        index += 1
        if device.StateFlags & win32con.DISPLAY_DEVICE_ATTACHED_TO_DESKTOP:
            mode = win32api.EnumDisplaySettings(
                device.DeviceName, win32con.ENUM_CURRENT_SETTINGS
            )
            yield mode.PelsWidth, mode.PelsHeight


def largest_resolution() -> str:
    """Largest monitor resolution as "WIDTHxHEIGHT", or "" if none is found."""
    largest = max(_resolutions(), key=lambda size: size[0] * size[1], default=None)
    return f"{largest[0]}x{largest[1]}" if largest else ""
