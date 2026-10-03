from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Protocol


@dataclass(frozen=True)
class Wallpaper:
    url: str  # image to download
    # Name to save it under. It must let the source recognise the file later
    # (see WallpaperSource.page_url), e.g. "wallhaven-<id>.jpg".
    filename: str


class WallpaperSource(Protocol):
    name: ClassVar[str]

    def random_wallpaper(self) -> Wallpaper: ...

    @staticmethod
    def page_url(wallpaper: Path) -> str | None:
        """The web page of a wallpaper this source downloaded, else None."""
        ...
