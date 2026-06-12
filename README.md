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
| `config`               | Configure the background agent interactively   |
| `service ...`          | Manage the background agent (see below)        |

## Background agent

Wallnext can run in the background and refresh the wallpaper on a schedule. It
runs as a **per-user agent** started by a Windows Scheduled Task at logon — not
a classic Windows service, because a service running in session 0 cannot change
the interactive desktop's wallpaper.

```bash
wallnext config            # interactive: interval, query, sorting, resolution…
wallnext service install   # register the logon task (hidden, auto-restart)
wallnext service start     # start it now without waiting for logon
wallnext service status    # show the scheduled task state
wallnext service stop      # stop the running agent
wallnext service uninstall # remove the task
```

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
