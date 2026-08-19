# MCP server

`journeycapture-mcp` exposes the thin client's REST API (`journeycapture.exe`,
running on a separate Windows machine) as MCP tools, so an MCP-aware assistant can
move the mouse, click, scroll, type, send key chords, and capture screenshots on that
machine.

It's controller-side only — it runs wherever your MCP client (Claude Code, Claude
Desktop, etc.) runs, not on the Windows box itself, and talks to `journeycapture.exe`
over the same HTTP API `scripts/*.py` use for live testing.

## Setup

```
uv sync --extra mcp
```

This is a separate step from the plain `uv sync` used for the thin client itself —
the MCP SDK isn't a dependency of `journeycapture.exe` or its Windows build.

## Configuration

Set via environment variables, read once at startup (`journeycapture_mcp/config.py`):

| Variable | Required | Default | Notes |
|---|---|---|---|
| `JOURNEYCAPTURE_HOST` | yes | — | IP or hostname of the Windows box |
| `JOURNEYCAPTURE_API_KEY` | yes | — | must match `journeycapture.exe`'s `config.json` |
| `JOURNEYCAPTURE_PORT` | no | `8443` | |
| `JOURNEYCAPTURE_SCHEME` | no | `http` | `http` or `https` |

Missing `JOURNEYCAPTURE_HOST`/`JOURNEYCAPTURE_API_KEY` fails fast with a clear message
on stderr rather than starting half-configured.

There's no built-in way to talk to more than one `journeycapture.exe` instance from a
single server process — each running `journeycapture-mcp` points at exactly one host.

## Running it

```
uv run journeycapture-mcp
```

Speaks MCP over stdio — it's meant to be spawned by an MCP client, not run
interactively. Add it to your client's MCP server config, e.g. a `.mcp.json` entry:

```json
{
  "mcpServers": {
    "journeycapture": {
      "command": "uv",
      "args": ["run", "--extra", "mcp", "journeycapture-mcp"],
      "cwd": "/path/to/JourneyCapture",
      "env": {
        "JOURNEYCAPTURE_HOST": "192.168.1.50",
        "JOURNEYCAPTURE_API_KEY": "your-real-api-key"
      }
    }
  }
}
```

## Tools

One tool per REST endpoint (`journeycapture_mcp/server.py`) — `health_check`,
`list_monitors`, `take_screenshot`, `move_mouse`, `click_mouse`, `scroll_mouse`,
`type_text`, `send_keys`. Tool descriptions mirror the REST API's own OpenAPI
descriptions (coordinate origin, scroll units, valid key names), so the same
reference in `CLAUDE.md`'s architecture section applies here too.

`take_screenshot` returns MCP image content (base64-encoded), not a file path or raw
bytes — nothing is written to disk on the controller side.

## Testing

`tests/test_mcp_client.py` and `tests/test_mcp_server.py` require the `mcp` extra;
they call `pytest.importorskip("mcp")` so they're skipped (not failed) when it isn't
installed — which is the normal state on the Windows build, since
`scripts/build_windows.ps1` only runs a plain `uv sync`. Run
`uv sync --extra mcp && uv run pytest -q` to include them.

No live Windows box is needed for these tests — `test_mcp_client.py` mocks the HTTP
layer with `httpx.MockTransport`, and `test_mcp_server.py` mocks `JourneyCaptureClient`
itself. For an actual end-to-end check against real hardware, use `health_check` first
(cheapest, no side effects), then `list_monitors`, the same order
`scripts/live_check.py` uses for the REST API directly.
