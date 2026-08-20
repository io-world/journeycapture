from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from journeycapture_thinclient import ws_client
from journeycapture_thinclient.config import ConfigError, load_config, resolve_config_path
from journeycapture_thinclient.logging_setup import configure_logging
from journeycapture_thinclient.winutil import set_dpi_awareness

logger = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="journeycapture")
    parser.add_argument("--config", default=None, help="Path to config.json")
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()

    config_path = resolve_config_path(args.config)
    try:
        config = load_config(config_path)
    except ConfigError as e:
        print(f"journeycapture: {e}", file=sys.stderr)
        sys.exit(1)

    configure_logging(config)
    logger.info("Loaded config from %s", config_path)

    set_dpi_awareness()

    asyncio.run(ws_client.run(config))


if __name__ == "__main__":
    main()
