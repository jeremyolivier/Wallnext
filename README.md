# Wallnext

![ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)
![ty](https://img.shields.io/badge/typed-ty-blue)

CLI to automatically set wallpapers from various sources.

## Setup

```bash
uv sync
uv run wallnext --help
```

## Settings window

Launch `wallnext` without a command (e.g. double-click the exe) to open the
settings window: the current wallpaper, the sources (each with its own
**Configure…** dialog) and the schedule.

## Commands

| Command        | Description                                     |
|----------------|-------------------------------------------------|
| `set-random`   | Set a random wallpaper as desktop background    |
| `schedule ...` | Refresh the wallpaper automatically (see below) |

## Automatic refresh

Wallnext refreshes the wallpaper on a schedule without any resident process: a
hidden **Windows Scheduled Task** fires at logon and then every configured
interval, and each run sets a single wallpaper and exits. A classic Windows
service is not an option, because it runs in session 0 and cannot change the
interactive desktop's wallpaper.

```bash
wallnext schedule install   # register the task (logon + every interval)
wallnext schedule start     # resume refreshes and change the wallpaper now
wallnext schedule stop      # pause refreshes
wallnext schedule status    # show the scheduled task state
wallnext schedule uninstall # remove the task
```

Search settings are re-read on every run. The interval (minimum 60 seconds) is
stored in the task trigger, so run `wallnext schedule install` again after
changing it.

Configuration (interval, query, sorting, resolution…) is stored in
`%APPDATA%\wallnext\config.toml` and logs in
`%APPDATA%\wallnext\wallnext.log`. Downloaded wallpapers are kept under
`%APPDATA%\wallnext\wallpapers` (only the current one: Windows needs it on
disk). Past wallpapers are listed, with their web address, in
`%APPDATA%\wallnext\history.jsonl` and the window's **History**.

## Install

```powershell
scoop install https://github.com/jeremyolivier/wallnext/releases/latest/download/wallnext.json
```

## Development

Tasks run with [just](https://just.systems) (`just` lists them):

```bash
just build            # compile the exe with Nuitka
just scoop-install    # build it and install it with Scoop
```

To release, bump the version in `pyproject.toml`, which commits and tags it,
then push: the tag starts the release workflow, which builds the exe and
publishes it with its Scoop manifest.

```bash
just bump minor       # or major, patch
git push --follow-tags
```

## Sources

Enable one or more in the window; each refresh picks one of them at random.

| Source | What | API key |
|---|---|---|
| [Wallhaven](https://wallhaven.cc) | Community wallpapers, by keywords | No |
| [NASA APOD](https://apod.nasa.gov) | Astronomy Picture of the Day archive | No |
| [NASA Images](https://images.nasa.gov) | NASA's image library, by keywords | No |
| [Wikimedia Commons](https://commons.wikimedia.org) | Pictures of the day | No |
| [Bing](https://www.bing.com) | Picture of the day, last 8 days | No |
| Windows Spotlight | Lock screen pictures | No |

Bing and Windows Spotlight use undocumented endpoints that may change.

## Examples

```bash
uv run wallnext set-random
uv run wallnext schedule status
```
