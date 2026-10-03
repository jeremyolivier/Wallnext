r"""The wallpapers shown so far, so a past one can be found again on the web.

Stored as JSON lines in %APPDATA%\wallnext\history.jsonl, newest last.
"""

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ValidationError

from wallnext import config

_MAX_ENTRIES = 500


class Entry(BaseModel):
    shown_at: datetime
    source: str
    url: str  # where the wallpaper lives on the web (page, or image)


def history_path() -> Path:
    return config.app_data_dir() / "history.jsonl"


def entries() -> list[Entry]:
    """Past wallpapers, newest first."""
    path = history_path()
    if not path.exists():
        return []
    result = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            result.append(Entry.model_validate_json(line))
        except ValidationError:
            continue  # a line cut short by a crash: skip it, keep the rest
    return result[::-1]


def record(source: str, url: str) -> None:
    """Add the wallpaper just shown, dropping the oldest past _MAX_ENTRIES."""
    entry = Entry(shown_at=datetime.now().astimezone(), source=source, url=url)
    kept = [*entries()[::-1], entry][-_MAX_ENTRIES:]
    path = history_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(e.model_dump_json() + "\n" for e in kept), encoding="utf-8")
