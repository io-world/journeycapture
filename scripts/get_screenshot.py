"""Fetch a single screenshot from a running journeycapture instance.

Run this from any machine that can reach the Windows box — it never runs on the
target itself.

Reads defaults from config.json next to this script (same file used by
send_text.py). Any CLI flag overrides the matching config value, so it also
works with no config file at all, e.g. run unmodified from VS Code's Run
button once the config file has host/api_key filled in. Saves into
screenshot_dir (same config key and default the MCP server's optional
local-saving feature uses, so both land in one shared folder) with a
timestamped filename, unless --out gives an exact path:

    uv run python scripts/get_screenshot.py
    uv run python scripts/get_screenshot.py --host 192.168.1.50 --api-key <key>
    uv run python scripts/get_screenshot.py --monitor 1 --format png --dir shots
    uv run python scripts/get_screenshot.py --out desktop.png
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
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
    parser.add_argument(
        "--dir", default=config.get("screenshot_dir", "screenshots"), help="Directory to save into"
    )
    parser.add_argument("--out", default=None, help="Exact output file path, overrides --dir/timestamp naming")
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
    ext = "png" if "png" in content_type else "jpeg"
    if args.out:
        out_path = Path(args.out)
    else:
        out_dir = Path(args.dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%f")
        out_path = out_dir / f"{timestamp}.{ext}"
    out_path.write_bytes(resp.content)
    print(f"saved {len(resp.content)} bytes to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
