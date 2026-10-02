import time
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.prompt import IntPrompt, Prompt
from rich.table import Table

from wallnext import config as cfg
from wallnext import scheduler
from wallnext.console import console, err_console
from wallnext.exceptions import WallnextError
from wallnext.refresh import logger, refresh, setup_file_logging
from wallnext.sources.wallhaven.client import WallhavenRequester
from wallnext.sources.wallhaven.source import WallhavenSource

app = typer.Typer(pretty_exceptions_enable=False)

DirOption = Annotated[
    Path | None,
    typer.Option(
        "--dir", "-d", help="Directory where wallpapers are saved. [default: from config]"
    ),
]
KeepOption = Annotated[
    int | None,
    typer.Option(
        "--keep", "-k", help="How many wallpapers to keep on disk. [default: from config]"
    ),
]


def _fail(e: WallnextError) -> typer.Exit:
    err_console.print(f"[bold red]Error:[/bold red] {e}")
    return typer.Exit(1)


@app.command(help="Fetch the most popular wallpapers of the last month.")
def get_top_wallpapers():
    try:
        result = WallhavenRequester().toplist()
    except WallnextError as e:
        raise _fail(e)
    console.print_json(result.model_dump_json(indent=2))


@app.command(help="Download a random wallpaper to ./wallpapers.")
def download_random():
    requester = WallhavenRequester()
    source = WallhavenSource(requester=requester, **cfg.load().search_params())
    try:
        dest = requester.download(source.random_url(), Path.cwd() / "wallpapers")
    except WallnextError as e:
        raise _fail(e)
    console.print(f"[green]✓[/green] Saved: [cyan]{dest}[/cyan]")


@app.command(help="Set a random wallpaper as desktop background.")
def set_random(dir: DirOption = None, keep: KeepOption = None):
    # Also the scheduled task's entry point: it has no console, so the outcome
    # is recorded in the log file.
    setup_file_logging()
    settings = cfg.load()
    try:
        dest = refresh(settings, dir or settings.download_dir, keep or settings.keep)
    except WallnextError as e:
        logger.warning("Refresh failed: %s", e)
        raise _fail(e)
    logger.info("Wallpaper set: %s", dest.name)
    console.print(f"[green]✓[/green] Wallpaper set: [cyan]{dest}[/cyan]")


@app.command(help="Change the wallpaper every N seconds until stopped.")
def slideshow(
    interval: Annotated[int, typer.Argument()] = 10,
    dir: DirOption = None,
    keep: KeepOption = None,
):
    settings = cfg.load()
    console.print(
        f"[cyan]Starting slideshow[/cyan] (interval: {interval}s). Press Ctrl+C to stop."
    )
    try:
        while True:
            try:
                refresh(settings, dir or settings.download_dir, keep or settings.keep)
                console.print("[green]✓[/green] Wallpaper updated.")
            except WallnextError as e:
                err_console.print(f"[yellow]Warning:[/yellow] {e} — retrying next cycle.")
            time.sleep(interval)
    except KeyboardInterrupt:
        console.print("\n[cyan]Slideshow stopped.[/cyan]")


@app.command(help="Configure wallpaper search and refresh interval interactively.")
def config():
    current = cfg.load()
    while (
        interval := IntPrompt.ask(
            "Interval between wallpaper changes (seconds, min 60)",
            default=current.interval_seconds,
        )
    ) < 60:
        err_console.print("[yellow]The interval must be at least 60 seconds.[/yellow]")
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
    purity = Prompt.ask("Purity bitmask (sfw/sketchy/nsfw)", default=current.purity)
    atleast = Prompt.ask(
        "Minimum resolution, e.g. 1920x1080 (empty for any)", default=current.atleast
    )
    settings = current.model_copy(
        update={
            "interval_seconds": interval,
            "query": query,
            "sorting": sorting,
            "toprange": toprange,
            "categories": categories,
            "purity": purity,
            "atleast": atleast,
        }
    )
    path = cfg.save(settings)
    console.print(f"[green]✓[/green] Config saved to [cyan]{path}[/cyan]")

    # The interval lives in the scheduled task's trigger.
    if interval != current.interval_seconds and scheduler.is_installed():
        try:
            scheduler.set_interval(interval)
        except WallnextError as e:
            raise _fail(e)
        console.print("[green]✓[/green] Schedule updated with the new interval.")


schedule_app = typer.Typer(
    help="Refresh the wallpaper automatically (Windows Task Scheduler)."
)
app.add_typer(schedule_app, name="schedule")


@schedule_app.command(help="Refresh at logon and every configured interval.")
def install():
    try:
        exe = scheduler.install(cfg.load().interval_seconds)
    except WallnextError as e:
        raise _fail(e)
    console.print(f"[green]✓[/green] Schedule installed ([cyan]{exe}[/cyan]).")


@schedule_app.command(help="Remove the scheduled task.")
def uninstall():
    try:
        scheduler.uninstall()
    except WallnextError as e:
        raise _fail(e)
    console.print("[green]✓[/green] Schedule removed.")


@schedule_app.command(help="Resume scheduled refreshes and change the wallpaper now.")
def start():
    try:
        scheduler.start()
    except WallnextError as e:
        raise _fail(e)
    console.print("[green]✓[/green] Refreshes resumed.")


@schedule_app.command(help="Pause scheduled refreshes.")
def stop():
    try:
        scheduler.stop()
    except WallnextError as e:
        raise _fail(e)
    console.print("[green]✓[/green] Refreshes paused.")


@schedule_app.command(help="Show the scheduled task status.")
def status():
    if not scheduler.is_installed():
        console.print(
            "Schedule not installed — run [cyan]wallnext schedule install[/cyan]."
        )
        return
    try:
        s = scheduler.status()
    except WallnextError as e:
        raise _fail(e)

    def when(moment: datetime | None) -> str:
        return f"{moment:%Y-%m-%d %H:%M:%S}" if moment else "—"

    if s.last_result is None:
        result = "—"
    elif s.last_result == 0:
        result = "[green]success[/green]"
    else:
        result = f"[red]failed (code {s.last_result:#x})[/red] — see {cfg.log_path()}"

    table = Table.grid(padding=(0, 2))
    table.add_row("State", s.state.name.lower())
    table.add_row("Command", s.command)
    table.add_row("Last run", when(s.last_run))
    table.add_row("Last result", result)
    table.add_row("Next run", when(s.next_run))
    console.print(table)


def main():
    app()


if __name__ == "__main__":
    main()
