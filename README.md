# Wallnext

![ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)
![ty](https://img.shields.io/badge/typed-ty-blue)

A Windows app that changes your desktop wallpaper on a schedule, with pictures
from Wallhaven, NASA, Wikimedia Commons, Bing or Windows Spotlight.

## Install

With [Scoop](https://scoop.sh):

```powershell
scoop install https://github.com/jeremyolivier/wallnext/releases/latest/download/wallnext.json
scoop update wallnext   # later, to get new versions
```

Without Scoop, download the zip of the
[latest release](https://github.com/jeremyolivier/wallnext/releases/latest),
extract it anywhere and run `wallnext.exe`.

## Usage

Open **Wallnext** from the Start menu:

- **Sources**: tick the sources to use and **Configure…** them. Each new
  wallpaper comes from one of the ticked sources, at random.
- **Wallpaper**: the current wallpaper and a link to its page, **Next
  wallpaper**, the **History** of past ones, and how often to change it.
- **About**: version, licenses, and what Wallnext stores.

The window does not need to stay open: a hidden Windows scheduled task changes
the wallpaper at logon and then at every interval, each run setting one picture
and exiting. (A Windows service could not do it: services cannot change the
desktop of the logged-in user.)

## Sources

| Source | Pictures | Settings |
|---|---|---|
| [Wallhaven](https://wallhaven.cc) | Community wallpapers | Keywords, sorting, resolution… or one of your collections |
| [NASA APOD](https://apod.nasa.gov) | Astronomy Picture of the Day, since 1995 | Minimum resolution |
| [NASA Images](https://images.nasa.gov) | NASA's image library | Keywords, minimum resolution |
| [Wikimedia Commons](https://commons.wikimedia.org) | Pictures of the day, since 2007 | Minimum resolution |
| [Bing](https://www.bing.com) | Picture of the day, last 8 days | — |
| Windows Spotlight | Lock screen pictures | — |

None needs an account. Wallhaven's API key is optional: it only gives access to
your private collections. Bing and Windows Spotlight use undocumented endpoints
that may change.

## Files

Everything lives in `%APPDATA%\wallnext`:

| File | Content |
|---|---|
| `config.toml` | Settings |
| `history.jsonl` | Past wallpapers, with their web address |
| `wallnext.log` | Log of the scheduled changes |
| `wallpapers\` | The current wallpaper only: Windows needs it on disk |

The Wallhaven API key is kept in the Windows Credential Manager
(`wallnext/wallhaven`), not in the config file.

## Development

Requires [uv](https://docs.astral.sh/uv/) and [just](https://just.systems).

```bash
uv sync
uv run wallnext       # open the window from source
just                  # list the tasks
just build            # compile the exe with Nuitka into build/main.dist
just run-build        # build it and launch it, without installing it
```

`wallnext set-random` sets one wallpaper and `wallnext schedule …` manages the
scheduled task: that is what the task and the window call. The packaged exe is
a windowed app, so these commands print nothing in a terminal; use `uv run
wallnext …` to see their output.

### Release

The version lives in `pyproject.toml`. `just bump` raises it, commits and tags
it; pushing the tag starts the release workflow, which builds the exe and
publishes it with its Scoop manifest.

```bash
just bump minor       # or major, patch
git push --follow-tags
```

## License

Wallnext is under the [MIT License](LICENSE). The exe also bundles third-party
software under its own licenses (Python, Qt and PySide6 under the LGPLv3, …),
listed in `THIRD-PARTY-NOTICES.txt` next to it and in the **About** page.
Pictures belong to their authors; Wallnext is not affiliated with the sources it
shows them from.
