import tempfile
import time
from pathlib import Path

import typer

from wallnext.console import console, err_console
from wallnext.exceptions import WallnextError
from wallnext.sources.base import WallpaperSource
from wallnext.sources.wallhaven import WallhavenSource
from wallnext.wallhaven.wallhaven_requester import WallhavenRequester
from wallnext.wallpaper import set_wallpaper

app = typer.Typer(pretty_exceptions_enable=False)

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
    try:
        result = wlhv_requester.toplist()
        console.print_json(result.model_dump_json(indent=2))
    except WallnextError as e:
        err_console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command(help="Download a random wallpaper from the top list.")
def download_random() -> None:
    try:
        url = source.random_url()
        dest = wlhv_requester.download(url, Path.cwd() / "wallpapers")
        console.print(f"[green]✓[/green] Saved: [cyan]{dest}[/cyan]")
    except WallnextError as e:
        err_console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command(help="Set a random wallpaper as desktop background.")
def set_random():
    try:
        _fetch_and_set(source)
        console.print("[green]✓[/green] Wallpaper set.")
    except WallnextError as e:
        err_console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command(help="Change the wallpaper every N seconds until stopped.")
def slideshow(interval: int = typer.Argument(default=10)):
    console.print(f"[cyan]Starting slideshow[/cyan] (interval: {interval}s). Press Ctrl+C to stop.")
    try:
        while True:
            try:
                _fetch_and_set(source)
                console.print("[green]✓[/green] Wallpaper updated.")
            except WallnextError as e:
                err_console.print(f"[yellow]Warning:[/yellow] {e} — retrying next cycle.")
            time.sleep(interval)
    except KeyboardInterrupt:
        console.print("\n[cyan]Slideshow stopped.[/cyan]")


def main():
    app()
