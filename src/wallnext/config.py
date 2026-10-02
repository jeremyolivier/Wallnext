import os
import tomllib
from pathlib import Path
from typing import Any

import tomli_w
from pydantic import BaseModel, Field

APP_NAME = "wallnext"


def app_data_dir() -> Path:
    """Per-user data directory, e.g. %APPDATA%\\wallnext."""
    base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(base) / APP_NAME


def config_path() -> Path:
    return app_data_dir() / "config.toml"


def log_path() -> Path:
    return app_data_dir() / "wallnext.log"


class Settings(BaseModel):
    """User-tunable settings for scheduled refreshes and one-shot commands."""

    interval_seconds: int = Field(default=600, ge=60)
    query: str = ""
    categories: str = "100"
    purity: str = "100"
    sorting: str = "toplist"
    toprange: str = "1M"
    atleast: str = ""
    ratios: str = ""
    download_dir: Path = Field(default_factory=lambda: app_data_dir() / "wallpapers")
    keep: int = Field(default=10, ge=1)

    def search_params(self) -> dict[str, Any]:
        """Map settings onto WallhavenRequester.search() keyword arguments."""
        return {
            "query": self.query,
            "categories": self.categories,
            "purity": self.purity,
            "sorting": self.sorting,
            "toprange": self.toprange,
            "atleast": self.atleast,
            "ratios": self.ratios,
        }


def load() -> Settings:
    """Read settings from disk, falling back to defaults when no config exists."""
    path = config_path()
    if not path.exists():
        return Settings()
    with path.open("rb") as f:
        data = tomllib.load(f)
    return Settings.model_validate(data)


def save(settings: Settings) -> Path:
    """Persist settings to the config file, creating parent dirs as needed."""
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # mode="json" turns Path into str so tomli_w can serialize it.
    with path.open("wb") as f:
        tomli_w.dump(settings.model_dump(mode="json"), f)
    return path