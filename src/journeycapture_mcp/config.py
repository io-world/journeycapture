from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Settings:
    host: str
    api_key: str
    port: int = 8443
    scheme: str = "http"
    timeout: float = 10.0
    # Where this MCP server itself listens (HTTP transport) — distinct from
    # host/port above, which are the Windows box's address, not this server's.
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8000
    # Off by default: every take_screenshot call also saves a timestamped copy
    # locally, for debugging what the model actually saw.
    save_screenshots: bool = False
    screenshot_dir: str = "screenshots"
    # Oldest files beyond this count get pruned after each save. 0 or negative
    # disables pruning (keep everything).
    max_saved_screenshots: int = 100


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

    host = data.get("host")
    if not host:
        raise ConfigError(f"{path}: 'host' is required (the Windows box's IP or hostname)")

    api_key = data.get("api_key")
    if not api_key:
        raise ConfigError(f"{path}: 'api_key' is required (must match journeycapture.exe's config.json)")

    try:
        return Settings(
            host=host,
            api_key=api_key,
            port=int(data.get("port", 8443)),
            scheme=data.get("scheme", "http"),
            timeout=float(data.get("timeout", 10.0)),
            mcp_host=data.get("mcp_host", "127.0.0.1"),
            mcp_port=int(data.get("mcp_port", 8000)),
            save_screenshots=bool(data.get("save_screenshots", False)),
            screenshot_dir=data.get("screenshot_dir", "screenshots"),
            max_saved_screenshots=int(data.get("max_saved_screenshots", 100)),
        )
    except (TypeError, ValueError) as e:
        raise ConfigError(f"{path}: invalid value: {e}") from e


def _load_settings_from_env() -> Settings:
    host = os.environ.get("JOURNEYCAPTURE_HOST")
    if not host:
        raise ConfigError(
            "JOURNEYCAPTURE_HOST is required (the Windows box's IP or hostname running journeycapture.exe)"
        )

    api_key = os.environ.get("JOURNEYCAPTURE_API_KEY")
    if not api_key:
        raise ConfigError("JOURNEYCAPTURE_API_KEY is required (must match journeycapture.exe's config.json)")

    port_raw = os.environ.get("JOURNEYCAPTURE_PORT", "8443")
    try:
        port = int(port_raw)
    except ValueError as e:
        raise ConfigError(f"JOURNEYCAPTURE_PORT must be an integer, got {port_raw!r}") from e

    scheme = os.environ.get("JOURNEYCAPTURE_SCHEME", "http")
    if scheme not in ("http", "https"):
        raise ConfigError(f"JOURNEYCAPTURE_SCHEME must be 'http' or 'https', got {scheme!r}")

    mcp_host = os.environ.get("JOURNEYCAPTURE_MCP_HOST", "127.0.0.1")

    mcp_port_raw = os.environ.get("JOURNEYCAPTURE_MCP_PORT", "8000")
    try:
        mcp_port = int(mcp_port_raw)
    except ValueError as e:
        raise ConfigError(f"JOURNEYCAPTURE_MCP_PORT must be an integer, got {mcp_port_raw!r}") from e

    save_screenshots = os.environ.get("JOURNEYCAPTURE_MCP_SAVE_SCREENSHOTS", "").lower() in ("1", "true", "yes")
    screenshot_dir = os.environ.get("JOURNEYCAPTURE_MCP_SCREENSHOT_DIR", "screenshots")

    max_saved_raw = os.environ.get("JOURNEYCAPTURE_MCP_MAX_SAVED_SCREENSHOTS", "100")
    try:
        max_saved_screenshots = int(max_saved_raw)
    except ValueError as e:
        raise ConfigError(
            f"JOURNEYCAPTURE_MCP_MAX_SAVED_SCREENSHOTS must be an integer, got {max_saved_raw!r}"
        ) from e

    return Settings(
        host=host,
        api_key=api_key,
        port=port,
        scheme=scheme,
        mcp_host=mcp_host,
        mcp_port=mcp_port,
        save_screenshots=save_screenshots,
        screenshot_dir=screenshot_dir,
        max_saved_screenshots=max_saved_screenshots,
    )
