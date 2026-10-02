# Wallnext

![ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)
![ty](https://img.shields.io/badge/typed-ty-blue)

CLI to automatically set wallpapers from various sources.

## Setup

```bash
uv sync
uv run wallnext --help
```

## Commands

| Command                | Description                                    |
|------------------------|------------------------------------------------|
| `get-top-wallpapers`   | List the top wallpapers of the last month      |
| `download-random`      | Download a random wallpaper to `./wallpapers/` |
| `set-random`           | Set a random wallpaper as desktop background   |
| `slideshow [interval]` | Change wallpaper every N seconds (default: 10) |
| `config`               | Configure search and refresh interval          |
| `schedule ...`         | Refresh the wallpaper automatically (see below)|

## Automatic refresh

Wallnext refreshes the wallpaper on a schedule without any resident process: a
hidden **Windows Scheduled Task** fires at logon and then every configured
interval, and each run sets a single wallpaper and exits. A classic Windows
service is not an option, because it runs in session 0 and cannot change the
interactive desktop's wallpaper.

```bash
wallnext config             # interactive: interval, query, sorting, resolution…
wallnext schedule install   # register the task (logon + every interval)
wallnext schedule start     # resume refreshes and change the wallpaper now
wallnext schedule stop      # pause refreshes
wallnext schedule status    # show the scheduled task state
wallnext schedule uninstall # remove the task
```

Search settings are re-read on every run. The interval (minimum 60 seconds) is
stored in the task trigger, so `wallnext config` re-registers the task when it
changes.

Configuration is stored in `%APPDATA%\wallnext\config.toml` and logs in
`%APPDATA%\wallnext\wallnext.log`. Downloaded wallpapers are kept under
`%APPDATA%\wallnext\wallpapers` (last 10 by default, configurable via `keep`).

## Sources

| Source | Status |
|---|---|
| [Wallhaven](https://wallhaven.cc) | ✅ Available |
| More coming soon | 🔜 |

## Examples

```bash
uv run wallnext set-random
uv run wallnext slideshow 30
```
