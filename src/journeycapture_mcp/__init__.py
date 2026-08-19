from __future__ import annotations

import sys

from journeycapture_mcp.client import JourneyCaptureClient
from journeycapture_mcp.config import ConfigError, load_settings
from journeycapture_mcp.server import build_server

__all__ = ["main"]


def main() -> None:
    try:
        settings = load_settings()
    except ConfigError as e:
        print(f"journeycapture-mcp: {e}", file=sys.stderr)
        sys.exit(1)

    client = JourneyCaptureClient(settings)
    server = build_server(client)
    server.run(transport="stdio")
