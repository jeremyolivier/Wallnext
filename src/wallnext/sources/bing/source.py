import random
import re
from pathlib import Path
from typing import ClassVar

from wallnext.sources.base import Wallpaper
from wallnext.sources.bing.client import BingRequester


class BingSource:
    name: ClassVar[str] = "Bing"

    def __init__(self, requester: BingRequester | None = None) -> None:
        self._requester = requester or BingRequester()

    def random_wallpaper(self) -> Wallpaper:
        image = random.choice(self._requester.archive().images)
        # The _UHD suffix serves the full-size picture (3840x2160 and up).
        image_id = image.urlbase.removeprefix("/th?id=OHR.")
        return Wallpaper(
            url=f"https://www.bing.com{image.urlbase}_UHD.jpg",
            filename=f"bing-{image_id}.jpg",
        )

    @staticmethod
    def page_url(wallpaper: Path) -> str | None:
        # Bing has no page per picture: link to the full-size image.
        match = re.fullmatch(r"bing-(.+)", wallpaper.stem)
        return f"https://www.bing.com/th?id=OHR.{match[1]}_UHD.jpg" if match else None
