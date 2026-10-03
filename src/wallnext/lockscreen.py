"""Set the lock screen picture, for the current user (no admin rights).

Through Windows.System.UserProfile.LockScreen. Windows copies the picture, so
the file may be deleted afterwards.
"""

import asyncio
from pathlib import Path

from winrt.windows.storage import StorageFile
from winrt.windows.system.userprofile import LockScreen

from wallnext.exceptions import WallnextError


def set_picture(picture: Path) -> None:
    async def apply() -> None:
        file = await StorageFile.get_file_from_path_async(str(picture.resolve()))
        await LockScreen.set_image_file_async(file)

    try:
        asyncio.run(apply())
    except OSError as e:
        raise WallnextError(f"Could not set the lock screen picture: {e}") from e
