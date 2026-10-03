"""Pictures kept on disk for the screensaver, which cannot wait for the network."""

import shutil
from pathlib import Path

from wallnext import config, sources
from wallnext.download import download
from wallnext.exceptions import WallnextError

# Enough variety for a long slideshow, without filling the disk.
MAX_PICTURES = 40
_FORMATS = {".jpg", ".jpeg", ".png"}


def folder() -> Path:
    return config.app_data_dir() / "screensaver"


def pictures() -> list[Path]:
    path = folder()
    if not path.exists():
        return []
    return [p for p in path.iterdir() if p.suffix.lower() in _FORMATS]


def _prune() -> None:
    """Keep only the MAX_PICTURES most recent pictures."""
    by_age = sorted(pictures(), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in by_age[MAX_PICTURES:]:
        old.unlink(missing_ok=True)


def add(picture: Path) -> None:
    """Keep a copy of a wallpaper that was just shown."""
    folder().mkdir(parents=True, exist_ok=True)
    shutil.copy2(picture, folder() / picture.name)
    _prune()


def fill(settings: config.Settings, count: int) -> int:
    """Download `count` new pictures from the enabled sources; returns how many."""
    folder().mkdir(parents=True, exist_ok=True)
    added = 0
    for _ in range(count * 2):  # some picks fail or are already cached
        if added == count:
            break
        try:
            wallpaper = sources.create(settings).random_wallpaper()
            dest = folder() / wallpaper.filename
            if dest.exists():
                continue
            download(wallpaper.url, dest)
        except WallnextError:
            continue
        added += 1
    _prune()
    return added
