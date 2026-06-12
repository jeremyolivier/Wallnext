import logging
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

from wallnext import config
from wallnext.exceptions import WallnextError
from wallnext.sources.wallhaven import WallhavenSource
from wallnext.wallhaven.wallhaven_requester import WallhavenRequester
from wallnext.wallpaper import set_wallpaper

logger = logging.getLogger("wallnext.agent")


def _setup_logging() -> None:
    """Log to a rotating file since the agent runs without a console."""
    path = config.log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        path, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)


def _prune(download_dir: Path, keep: int) -> None:
    """Keep only the most recent `keep` wallpapers on disk."""
    files = sorted(download_dir.glob("*"), key=lambda p: p.stat().st_mtime)
    for old in files[:-keep]:
        old.unlink(missing_ok=True)


def _cycle(
    requester: WallhavenRequester, source: WallhavenSource, settings: config.Settings
) -> None:
    url = source.random_url()
    settings.download_dir.mkdir(parents=True, exist_ok=True)
    dest = requester.download(url, settings.download_dir)
    set_wallpaper(dest)
    _prune(settings.download_dir, settings.keep)


def run_agent() -> None:
    """Background loop: fetch a wallpaper, apply it, sleep, repeat."""
    _setup_logging()
    settings = config.load()
    requester = WallhavenRequester()
    source = WallhavenSource(requester=requester, **settings.search_params())
    logger.info("Agent started (interval=%ss)", settings.interval_seconds)
    while True:
        try:
            _cycle(requester, source, settings)
            logger.info("Wallpaper updated.")
        except WallnextError as e:
            logger.warning("Cycle failed: %s — retrying next cycle.", e)
        except Exception:
            logger.exception("Unexpected error — retrying next cycle.")
        time.sleep(settings.interval_seconds)
