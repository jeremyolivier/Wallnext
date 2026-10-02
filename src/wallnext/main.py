import time
from pathlib import Path
from typing import Annotated

import typer
from rich.prompt import IntPrompt, Prompt

from wallnext import config as cfg
from wallnext.console import console, err_console
from wallnext.exceptions import WallnextError
from wallnext.service.agent import _prune
from wallnext.sources.base import WallpaperSource
from wallnext.sources.wallhaven.client import WallhavenRequester
from wallnext.sources.wallhaven.source import WallhavenSource
from wallnext.wallpaper import set_wallpaper

app = typer.Typer(pretty_exceptions_enable=False)

_settings = cfg.load()
wlhv_requester = WallhavenRequester()
source: WallpaperSource = WallhavenSource(
    requester=wlhv_requester, **_settings.search_params()
)

DirOption = Annotated[
    Path,
    typer.Option("--dir", "-d", help="Directory where wallpapers are saved."),
]
KeepOption = Annotated[
    int,
    typer.Option("--keep", "-k", help="How many wallpapers to keep on disk."),
]


def _fetch_and_set(source: WallpaperSource, dest_dir: Path, keep: int) -> None:
    # Persist the image: Windows reads this path from the registry on every
    # logon, so deleting it (as a temp file) leaves a black desktop after reboot.
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = wlhv_requester.download(source.random_url(), dest_dir)
    set_wallpaper(dest)
    _prune(dest_dir, keep)


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
def set_random(
    dir: DirOption = _settings.download_dir,
    keep: KeepOption = _settings.keep,
):
    try:
        _fetch_and_set(source, dir, keep)
        console.print(f"[green]✓[/green] Wallpaper set ([cyan]{dir}[/cyan]).")
    except WallnextError as e:
        err_console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command(help="Change the wallpaper every N seconds until stopped.")
def slideshow(
    interval: Annotated[int, typer.Argument()] = 10,
    dir: DirOption = _settings.download_dir,
    keep: KeepOption = _settings.keep,
):
    console.print(f"[cyan]Starting slideshow[/cyan] (interval: {interval}s). Press Ctrl+C to stop.")
    try:
        while True:
            try:
                _fetch_and_set(source, dir, keep)
                console.print("[green]✓[/green] Wallpaper updated.")
            except WallnextError as e:
                err_console.print(f"[yellow]Warning:[/yellow] {e} — retrying next cycle.")
            time.sleep(interval)
    except KeyboardInterrupt:
        console.print("\n[cyan]Slideshow stopped.[/cyan]")


@app.command(help="Configure the background agent interactively.")
def config():
    current = cfg.load()
    interval = IntPrompt.ask(
        "Interval between wallpaper changes (seconds)",
        default=current.interval_seconds,
    )
    query = Prompt.ask("Search query (empty for none)", default=current.query)
    sorting = Prompt.ask(
        "Sorting",
        choices=["toplist", "random", "date_added", "views", "favorites"],
        default=current.sorting,
    )
    toprange = Prompt.ask("Top range (for toplist)", default=current.toprange)
    categories = Prompt.ask(
        "Categories bitmask (general/anime/people)", default=current.categories
    )
    purity = Prompt.ask(
        "Purity bitmask (sfw/sketchy/nsfw)", default=current.purity
    )
    atleast = Prompt.ask(
        "Minimum resolution, e.g. 1920x1080 (empty for any)", default=current.atleast
    )
    settings = cfg.Settings(
        interval_seconds=interval,
        query=query,
        sorting=sorting,
        toprange=toprange,
        categories=categories,
        purity=purity,
        atleast=atleast,
        download_dir=current.download_dir,
        keep=current.keep,
    )
    path = cfg.save(settings)
    console.print(f"[green]✓[/green] Config saved to [cyan]{path}[/cyan]")


service_app = typer.Typer(
    help="Manage the background wallpaper agent (Windows scheduled task)."
)
app.add_typer(service_app, name="service")


@service_app.command(help="Install the agent to start automatically at logon.")
def install():
    from wallnext.service import manager

    try:
        manager.install()
    except WallnextError as e:
        err_console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)
    console.print(
        "[green]✓[/green] Agent installed. It starts at next logon — "
        "use [cyan]wallnext service start[/cyan] to run it now."
    )


@service_app.command(help="Remove the agent's scheduled task.")
def uninstall():
    from wallnext.service import manager

    try:
        manager.uninstall()
    except WallnextError as e:
        err_console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)
    console.print("[green]✓[/green] Agent uninstalled.")


@service_app.command(help="Start the agent now.")
def start():
    from wallnext.service import manager

    try:
        manager.start()
    except WallnextError as e:
        err_console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)
    console.print("[green]✓[/green] Agent started.")


@service_app.command(help="Stop the running agent.")
def stop():
    from wallnext.service import manager

    try:
        manager.stop()
    except WallnextError as e:
        err_console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)
    console.print("[green]✓[/green] Agent stopped.")


@service_app.command(help="Show the agent's scheduled task status.")
def status():
    from wallnext.service import manager

    try:
        console.print(manager.status())
    except WallnextError as e:
        err_console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@service_app.command(help="Run the agent loop in the foreground (used by the scheduled task).")
def run():
    from wallnext.service.agent import run_agent

    run_agent()


def main():
    app()


if __name__ == "__main__":
    main()
