"""Fetch a single screenshot from a running journeycapture instance.

Run this from any machine that can reach the Windows box — it never runs on the
target itself.

Reads defaults from config.json next to this script (same file used by
send_text.py). Any CLI flag overrides the matching config value, so it also
works with no config file at all, e.g. run unmodified from VS Code's Run
button once the config file has host/api_key filled in:

    uv run python scripts/get_screenshot.py
    uv run python scripts/get_screenshot.py --host 192.168.1.50 --api-key <key>
    uv run python scripts/get_screenshot.py --monitor 1 --format png --out desktop.png
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import httpx

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
    parser.add_argument(
        "--monitor", type=int, default=config.get("monitor"), help="Monitor index (default: server config)"
    )
    parser.add_argument("--format", choices=["png", "jpeg"], default=config.get("format"), help="Default: server config")
    parser.add_argument(
        "--quality", type=int, default=config.get("quality"), help="JPEG quality 1-100 (default: server config)"
    )
    parser.add_argument("--out", default=config.get("out"), help="Output file path (default: screenshot.<ext>)")
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
    params = {}
    if args.format is not None:
        params["format"] = args.format
    if args.quality is not None:
        params["quality"] = args.quality
    if args.monitor is not None:
        params["monitor"] = args.monitor

    try:
        resp = httpx.get(
            f"{base_url}/screenshot",
            headers={"X-API-Key": args.api_key},
            params=params,
            timeout=args.timeout,
        )
    except httpx.HTTPError as e:
        print(f"request error: {e}", file=sys.stderr)
        return 1

    if resp.status_code != 200:
        print(f"FAIL: status={resp.status_code} body={resp.text}", file=sys.stderr)
        return 1

    content_type = resp.headers.get("content-type", "")
    ext = "png" if "png" in content_type else "jpg"
    out_path = Path(args.out) if args.out else Path(f"screenshot.{ext}")
    out_path.write_bytes(resp.content)
    print(f"saved {len(resp.content)} bytes to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
