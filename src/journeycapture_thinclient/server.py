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

    try:
        asyncio.run(ws_client.run(config))
    except ws_client.RegistrationRejected as e:
        # Not recoverable by retrying — the broker rejected machine_id/api_key
        # themselves, not a transient network issue. Exit non-zero so this is
        # distinguishable from a normal shutdown by anything checking the exit code.
        logger.error("broker rejected this machine's credentials: %s", e)
        print(f"journeycapture: broker rejected this machine's credentials: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
