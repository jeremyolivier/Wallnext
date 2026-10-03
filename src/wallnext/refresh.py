import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from wallnext import config, history, lockscreen, sources
from wallnext.download import download
from wallnext.exceptions import WallnextError
from wallnext.screensaver import cache as screensaver_cache
from wallnext.screensaver import windows as screensaver
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


def _remove_others(download_dir: Path, current: Path) -> None:
    """Delete past wallpapers except the current one.

    Only files a source recognises are touched: `--dir` may hold other files.
    """
    for old in download_dir.iterdir():
        if old.is_file() and old != current and sources.identify(old):
            old.unlink(missing_ok=True)


def refresh(settings: config.Settings, dest_dir: Path) -> Path:
    """Download a wallpaper matching `settings`, apply it, and record it."""
    source = sources.create(settings)
    wallpaper = source.random_wallpaper()
    # Keep the image on disk: Windows reads this path from the registry on every
    # logon, so deleting it (as a temp file) leaves a black desktop after reboot.
    dest = download(wallpaper.url, dest_dir / wallpaper.filename)
    set_wallpaper(dest)
    _remove_others(dest_dir, dest)
    if settings.lock_screen:
        try:
            lockscreen.set_picture(dest)
        except WallnextError as e:  # the wallpaper itself is set
            logger.warning("%s", e)
    if screensaver.is_enabled():
        try:
            screensaver_cache.add(dest)
        except OSError as e:  # the wallpaper is set: a cache miss is not fatal
            logger.warning("Screensaver cache: %s", e)
    history.record(source.name, source.page_url(dest) or wallpaper.url)
    return dest
