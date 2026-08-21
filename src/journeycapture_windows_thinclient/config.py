from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError


class ScreenshotConfig(BaseModel, extra="forbid"):
    format: Literal["png", "jpeg"] = "jpeg"
    quality: int = Field(default=75, ge=1, le=100)
    monitor: int = Field(default=0, ge=0)


class Config(BaseModel, extra="forbid"):
    broker_host: str
    broker_port: int = Field(default=8601, ge=1, le=65535)
    machine_id: str = Field(min_length=1, description="Identifies this machine to the broker; must match one of the broker's configured machine IDs.")
    api_key: str = Field(min_length=16, description="Must match this machine_id's key in the broker's own config.")
    screenshot: ScreenshotConfig = Field(default_factory=ScreenshotConfig)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_file: str = "journeycapture.log"


class ConfigError(Exception):
    pass


def default_config_path() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        base = Path.cwd()
    return base / "config.json"


def resolve_config_path(cli_path: str | None) -> Path:
    if cli_path:
        return Path(cli_path)
    env_path = os.environ.get("JOURNEYCAPTURE_CONFIG")
    if env_path:
        return Path(env_path)
    return default_config_path()


def load_config(path: Path) -> Config:
    if not path.is_file():
        raise ConfigError(
            f"Config file not found: {path}\n"
            "Copy examples/config.example.json to config.json next to the executable, "
            "set broker_host/machine_id/api_key to match the broker's config before running."
        )
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise ConfigError(f"Config file at {path} is not valid JSON: {e}") from e
    try:
        return Config.model_validate(data)
    except ValidationError as e:
        raise ConfigError(f"Config file at {path} failed validation:\n{e}") from e
