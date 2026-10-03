import os
import tomllib
from pathlib import Path
from typing import Any

import tomli_w
from pydantic import BaseModel, Field, model_validator

from wallnext.display import largest_resolution

APP_NAME = "wallnext"


def app_data_dir() -> Path:
    """Per-user data directory, e.g. %APPDATA%\\wallnext."""
    base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(base) / APP_NAME


def config_path() -> Path:
    return app_data_dir() / "config.toml"


def log_path() -> Path:
    return app_data_dir() / "wallnext.log"


class SourceSettings(BaseModel):
    """Settings every source has: whether it takes part in the random pick."""

    enabled: bool = True


class WallhavenSettings(SourceSettings):
    query: str = ""
    categories: str = "100"
    purity: str = "100"
    sorting: str = "toplist"
    toprange: str = "1M"
    atleast: str = Field(default_factory=largest_resolution)
    ratios: str = ""

    def search_params(self) -> dict[str, Any]:
        """Map settings onto WallhavenRequester.search() keyword arguments."""
        return self.model_dump(exclude={"enabled"})


class ApodSettings(SourceSettings):
    enabled: bool = False
    atleast: str = Field(default_factory=largest_resolution)


class SourcesSettings(BaseModel):
    """One table per source, e.g. [sources.wallhaven] in config.toml."""

    wallhaven: WallhavenSettings = Field(default_factory=WallhavenSettings)
    apod: ApodSettings = Field(default_factory=ApodSettings)


class Settings(BaseModel):
    """User-tunable settings for scheduled refreshes and one-shot commands."""

    interval_seconds: int = Field(default=600, ge=60)
    download_dir: Path = Field(default_factory=lambda: app_data_dir() / "wallpapers")
    keep: int = Field(default=10, ge=1)
    sources: SourcesSettings = Field(default_factory=SourcesSettings)

    def source(self, key: str) -> SourceSettings:
        """The settings of the source keyed `key`, e.g. "wallhaven"."""
        return getattr(self.sources, key)

    def with_source(self, key: str, **changes: Any) -> Settings:
        """A copy with `changes` applied to the settings of source `key`."""
        updated = self.source(key).model_copy(update=changes)
        return self.model_copy(
            update={"sources": self.sources.model_copy(update={key: updated})}
        )

    @model_validator(mode="before")
    @classmethod
    def _migrate_flat_wallhaven(cls, data: Any) -> Any:
        # Before multiple sources, Wallhaven's settings sat at the top level.
        if not isinstance(data, dict):
            return data
        legacy = {
            k: data.pop(k) for k in list(data) if k in WallhavenSettings.model_fields
        }
        data.pop("source", None)
        if legacy:
            sources = data.setdefault("sources", {})
            sources.setdefault("wallhaven", {}).update(legacy)
        return data


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
