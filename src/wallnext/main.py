from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from wallnext import config as cfg
from wallnext import scheduler
from wallnext.console import console, err_console
from wallnext.exceptions import WallnextError
from wallnext.refresh import logger, refresh, setup_file_logging

app = typer.Typer(pretty_exceptions_enable=False)

DirOption = Annotated[
    Path | None,
    typer.Option(
        "--dir",
        "-d",
        help="Directory where wallpapers are saved. [default: from config]",
    ),
]


@app.callback(invoke_without_command=True)
def default(ctx: typer.Context):
    # Launched without a command (e.g. double-click): open the settings window.
    if ctx.invoked_subcommand is None:
        from wallnext import gui  # lazy: keeps Qt out of the scheduled runs

        gui.run()


def _fail(e: WallnextError) -> typer.Exit:
    err_console.print(f"[bold red]Error:[/bold red] {e}")
    return typer.Exit(1)


@app.command(help="Set a random wallpaper as desktop background.")
def set_random(dir: DirOption = None):
    # Also the scheduled task's entry point: it has no console, so the outcome
    # is recorded in the log file.
    setup_file_logging()
    settings = cfg.load()
    try:
        dest = refresh(settings, dir or settings.download_dir)
    except WallnextError as e:
        logger.warning("Refresh failed: %s", e)
        raise _fail(e)
    logger.info("Wallpaper set: %s", dest.name)
    console.print(f"[green]✓[/green] Wallpaper set: [cyan]{dest}[/cyan]")


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
