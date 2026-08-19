"""Type text into whatever window has focus on a running journeycapture instance.

Run this from any machine that can reach the Windows box — it never runs on the
target itself. Types into whatever window currently has focus there, so make
sure the right window is focused before running it.

Reads defaults from config.json next to this script (same file used by
get_screenshot.py). Any CLI flag overrides the matching config value:

    uv run python scripts/send_text.py --text "hello world"
    uv run python scripts/send_text.py --host 192.168.1.50 --api-key <key> --text "hi"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import httpx

TEXT = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.\n\n "

CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    return json.loads(CONFIG_PATH.read_text())


def parse_args() -> argparse.Namespace:
    config = load_config()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default=config.get("host"), help="IP or hostname of the journeycapture instance")
    parser.add_argument("--port", type=int, default=config.get("port", 8443))
    parser.add_argument("--scheme", default=config.get("scheme", "http"), choices=["http", "https"])
    parser.add_argument(
        "--api-key",
        default=config.get("api_key") or os.environ.get("JOURNEYCAPTURE_API_KEY"),
        help=f"Defaults to {CONFIG_PATH.name}'s api_key, then the JOURNEYCAPTURE_API_KEY env var",
    )
    parser.add_argument("--text", default=TEXT, help="Text to type on the remote machine")
    parser.add_argument("--timeout", type=float, default=config.get("timeout", 10.0))
    args = parser.parse_args()

    if not args.host:
        parser.error(f"--host is required (or set 'host' in {CONFIG_PATH.name})")
    if not args.api_key:
        parser.error(f"--api-key is required (or set 'api_key' in {CONFIG_PATH.name}, or JOURNEYCAPTURE_API_KEY)")
    return args


def main() -> int:
    args = parse_args()
    base_url = f"{args.scheme}://{args.host}:{args.port}"

    try:
        resp = httpx.post(
            f"{base_url}/keyboard/type",
            headers={"X-API-Key": args.api_key},
            json={"text": args.text},
            timeout=args.timeout,
        )
    except httpx.HTTPError as e:
        print(f"request error: {e}", file=sys.stderr)
        return 1

    if resp.status_code != 200:
        print(f"FAIL: status={resp.status_code} body={resp.text}", file=sys.stderr)
        return 1

    body = resp.json()
    print(f"typed {body.get('length')} character(s) — verify it landed in the right window")
    return 0


if __name__ == "__main__":
    sys.exit(main())
