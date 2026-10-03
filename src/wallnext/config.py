import os
import tomllib
from pathlib import Path
from typing import Any, Literal

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
    # Collection mode. The API key is in the Credential Manager, not here.
    mode: Literal["search", "collection"] = "search"
    username: str = ""
    collection_id: int | None = None
    collection_label: str = ""

    def search_params(self) -> dict[str, Any]:
        """Map settings onto WallhavenRequester.search() keyword arguments."""
        return self.model_dump(
            exclude={"enabled", "mode", "username", "collection_id", "collection_label"}
        )


class ApodSettings(SourceSettings):
    enabled: bool = False
    atleast: str = Field(default_factory=largest_resolution)


class NasaImagesSettings(SourceSettings):
    enabled: bool = False
    query: str = "galaxy"
    atleast: str = Field(default_factory=largest_resolution)


class WikimediaSettings(SourceSettings):
    enabled: bool = False
    atleast: str = Field(default_factory=largest_resolution)


class BingSettings(SourceSettings):
    enabled: bool = False


class SpotlightSettings(SourceSettings):
    enabled: bool = False


class SourcesSettings(BaseModel):
    """One table per source, e.g. [sources.wallhaven] in config.toml."""

    wallhaven: WallhavenSettings = Field(default_factory=WallhavenSettings)
    apod: ApodSettings = Field(default_factory=ApodSettings)
    nasa_images: NasaImagesSettings = Field(default_factory=NasaImagesSettings)
    wikimedia: WikimediaSettings = Field(default_factory=WikimediaSettings)
    bing: BingSettings = Field(default_factory=BingSettings)
    spotlight: SpotlightSettings = Field(default_factory=SpotlightSettings)


class Settings(BaseModel):
    """User-tunable settings for scheduled refreshes and one-shot commands."""

    interval_seconds: int = Field(default=600, ge=60)
    download_dir: Path = Field(default_factory=lambda: app_data_dir() / "wallpapers")
    lock_screen: bool = False  # also set each wallpaper as the lock screen
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
    # mode="json" turns Path into str; TOML has no null, so unset values are
    # left out and come back as their default on load.
    text = tomli_w.dumps(settings.model_dump(mode="json", exclude_none=True))
    # Write a temporary file and swap it in: a failure never leaves the
    # config half written.
    tmp = path.with_suffix(".toml.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    return path
