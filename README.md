# Wallnext

![ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)
![ty](https://img.shields.io/badge/typed-ty-blue)

CLI to automatically set wallpapers from various sources.

## Setup

```bash
cp .env.example .env
# Fill in your API key in .env
uv sync
uv run wallnext --help
```

Get your Wallhaven API key at [wallhaven.cc/settings/account](https://wallhaven.cc/settings/account).

## Commands

| Command                | Description                                    |
|------------------------|------------------------------------------------|
| `get-top-wallpapers`   | List the top wallpapers of the last month      |
| `download-random`      | Download a random wallpaper to `./wallpapers/` |
| `set-random`           | Set a random wallpaper as desktop background   |
| `slideshow [interval]` | Change wallpaper every N seconds (default: 10) |

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
