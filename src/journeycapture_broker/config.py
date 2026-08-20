from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Settings:
    api_key: str  # MCP-facing secret for the HTTP API
    machines: dict[str, str] = field(default_factory=dict)  # machine_id -> api_key
    host: str = "0.0.0.0"
    http_port: int = 8600
    ws_host: str = "0.0.0.0"
    ws_port: int = 8601
    request_timeout: float = 15.0


def load_settings(config_path: str | Path | None = None) -> Settings:
    if config_path is not None:
        return _load_settings_from_file(Path(config_path))
    return _load_settings_from_env()


def _load_settings_from_file(path: Path) -> Settings:
    if not path.is_file():
        raise ConfigError(f"Config file not found: {path}")
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise ConfigError(f"Config file at {path} is not valid JSON: {e}") from e

    api_key = data.get("api_key")
    if not api_key:
        raise ConfigError(f"{path}: 'api_key' is required (the MCP-facing secret)")

    machines = data.get("machines")
    if not machines:
        raise ConfigError(f"{path}: 'machines' is required — an object of machine_id: api_key pairs")

    try:
        return Settings(
            api_key=api_key,
            machines=dict(machines),
            host=data.get("host", "0.0.0.0"),
            http_port=int(data.get("http_port", 8600)),
            ws_host=data.get("ws_host", "0.0.0.0"),
            ws_port=int(data.get("ws_port", 8601)),
            request_timeout=float(data.get("request_timeout", 15.0)),
        )
    except (TypeError, ValueError) as e:
        raise ConfigError(f"{path}: invalid value: {e}") from e


def _load_settings_from_env() -> Settings:
    api_key = os.environ.get("JOURNEYCAPTURE_BROKER_API_KEY")
    if not api_key:
        raise ConfigError("JOURNEYCAPTURE_BROKER_API_KEY is required")

    machines_raw = os.environ.get("JOURNEYCAPTURE_BROKER_MACHINES")
    if not machines_raw:
        raise ConfigError(
            "JOURNEYCAPTURE_BROKER_MACHINES is required — a JSON object of machine_id: api_key pairs"
        )
    try:
        machines = json.loads(machines_raw)
    except json.JSONDecodeError as e:
        raise ConfigError(f"JOURNEYCAPTURE_BROKER_MACHINES is not valid JSON: {e}") from e

    host = os.environ.get("JOURNEYCAPTURE_BROKER_HOST", "0.0.0.0")
    ws_host = os.environ.get("JOURNEYCAPTURE_BROKER_WS_HOST", "0.0.0.0")

    try:
        http_port = int(os.environ.get("JOURNEYCAPTURE_BROKER_HTTP_PORT", "8600"))
        ws_port = int(os.environ.get("JOURNEYCAPTURE_BROKER_WS_PORT", "8601"))
    except ValueError as e:
        raise ConfigError(f"JOURNEYCAPTURE_BROKER_HTTP_PORT/_WS_PORT must be integers: {e}") from e

    return Settings(
        api_key=api_key,
        machines=machines,
        host=host,
        http_port=http_port,
        ws_host=ws_host,
        ws_port=ws_port,
    )
