from typing import Protocol


class WallpaperSource(Protocol):
    def random_url(self) -> str: ...
