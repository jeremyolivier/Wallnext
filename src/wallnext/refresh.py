import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from wallnext import config, sources
from wallnext.download import download
from wallnext.wallpaper import set_wallpaper

logger = logging.getLogger("wallnext")


def setup_file_logging() -> None:
    """Log to a rotating file: scheduled runs have no console to report to."""
    path = config.log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        path, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)


def prune(download_dir: Path, keep: int) -> None:
    """Keep only the most recent `keep` wallpapers on disk."""
    files = sorted(download_dir.glob("*"), key=lambda p: p.stat().st_mtime)
    for old in files[:-keep]:
        old.unlink(missing_ok=True)


def refresh(settings: config.Settings, dest_dir: Path, keep: int) -> Path:
    """Download a wallpaper matching `settings`, apply it, and prune old ones."""
    wallpaper = sources.create(settings).random_wallpaper()
    # Persist the image: Windows reads this path from the registry on every
    # logon, so deleting it (as a temp file) leaves a black desktop after reboot.
    dest = download(wallpaper.url, dest_dir / wallpaper.filename)
    set_wallpaper(dest)
    prune(dest_dir, keep)
    return dest
