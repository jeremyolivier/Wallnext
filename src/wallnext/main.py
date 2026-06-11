import tempfile
import time
from pathlib import Path

import typer

from wallnext.sources.base import WallpaperSource
from wallnext.sources.wallhaven import WallhavenSource
from wallnext.wallhaven.wallhaven_requester import WallhavenRequester
from wallnext.wallpaper import set_wallpaper

app = typer.Typer()

source: WallpaperSource = WallhavenSource()
wlhv_requester = WallhavenRequester()


def _fetch_and_set(source: WallpaperSource) -> None:
    url = source.random_url()
    suffix = Path(url).suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        wlhv_requester.download(url, tmp_path.parent, filename=tmp_path.name)
        set_wallpaper(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)


@app.command(help="Fetch the most popular wallpapers of the last month.")
def get_top_wallpapers():
    result = wlhv_requester.toplist()
    print(result.model_dump_json(indent=2))


@app.command(help="Download a random wallpaper from the top list.")
def download_random() -> Path:
    url = source.random_url()
    dest = wlhv_requester.download(url, Path.cwd() / "wallpapers")
    typer.echo(f"Saved: {dest}")
    return dest


@app.command(help="Set a random wallpaper as desktop background.")
def set_random():
    _fetch_and_set(source)
    typer.echo("Wallpaper set.")


@app.command(help="Change the wallpaper every N seconds until stopped.")
def slideshow(interval: int = typer.Argument(default=10)):
    typer.echo("Starting slideshow. Press Ctrl+C to stop.")
    try:
        while True:
            _fetch_and_set(source)
            time.sleep(interval)
    except KeyboardInterrupt:
        typer.echo("Slideshow stopped.")


def main():
    app()
