from __future__ import annotations

import argparse
import sys

from journeycapture_mcp.client import JourneyCaptureClient
from journeycapture_mcp.config import ConfigError, load_settings
from journeycapture_mcp.server import build_server

__all__ = ["main"]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="journeycapture-mcp")
    parser.add_argument(
        "--config",
        default=None,
        help="Path to a JSON config file (e.g. scripts/config.json) with host/api_key/etc. "
        "Overrides the JOURNEYCAPTURE_* environment variables when given.",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    try:
        settings = load_settings(args.config)
    except ConfigError as e:
        print(f"journeycapture-mcp: {e}", file=sys.stderr)
        sys.exit(1)

    client = JourneyCaptureClient(settings)
    server = build_server(client)
    server.run(transport="streamable-http", host=settings.mcp_host, port=settings.mcp_port)
