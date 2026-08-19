from __future__ import annotations

import os
from dataclasses import dataclass


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


def load_settings() -> Settings:
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

    return Settings(
        host=host, api_key=api_key, port=port, scheme=scheme, mcp_host=mcp_host, mcp_port=mcp_port
    )
