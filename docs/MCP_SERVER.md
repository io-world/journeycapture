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

Two ways to configure it — a JSON file or environment variables. `journeycapture_mcp/config.py`
uses the file when `--config` is given, otherwise falls back to the environment variables.

**File** (`--config PATH`): the same shape as `scripts/config.json`, so you can point
straight at the one you already have:

```
uv run journeycapture-mcp --config scripts/config.json
```

Recognized keys: `host`, `api_key` (both required), `port` (default `8443`), `scheme`
(default `"http"`), `timeout`, `mcp_host` (default `"127.0.0.1"`), `mcp_port` (default
`8000`). Extra keys `scripts/config.json` has for the other scripts (`monitor`,
`format`, `quality`, `out`) are simply ignored.

**Environment variables** (used only when `--config` isn't given):

| Variable | Required | Default | Notes |
|---|---|---|---|
| `JOURNEYCAPTURE_HOST` | yes | — | IP or hostname of the Windows box |
| `JOURNEYCAPTURE_API_KEY` | yes | — | must match `journeycapture.exe`'s `config.json` |
| `JOURNEYCAPTURE_PORT` | no | `8443` | the Windows box's port |
| `JOURNEYCAPTURE_SCHEME` | no | `http` | `http` or `https`, for reaching the Windows box |
| `JOURNEYCAPTURE_MCP_HOST` | no | `127.0.0.1` | where **this** server itself listens |
| `JOURNEYCAPTURE_MCP_PORT` | no | `8000` | where **this** server itself listens |

Either way, a missing host/api_key fails fast with a clear message on stderr rather
than starting half-configured.

There's no built-in way to talk to more than one `journeycapture.exe` instance from a
single server process — each running `journeycapture-mcp` points at exactly one host.

Don't confuse the two host/port pairs: `host`/`port` (or `JOURNEYCAPTURE_HOST`/`_PORT`)
is where the Windows box is; `mcp_host`/`mcp_port` (or `JOURNEYCAPTURE_MCP_HOST`/`_PORT`)
is where this server binds for its own MCP clients to connect to.

## Running it

This server speaks MCP over **streamable HTTP**, not stdio — you start it yourself,
separately from your MCP client, and it keeps running until you stop it:

```
uv run journeycapture-mcp --config scripts/config.json
```

By default it binds `127.0.0.1:8000` — loopback only, so nothing off this machine can
reach it. Then point your MCP client at it, e.g. a `.mcp.json` entry:

```json
{
  "mcpServers": {
    "journeycapture": {
      "type": "http",
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```

**Security note:** this server holds the real `journeycapture_thinclient` API key
internally and has no authentication of its own at the MCP/HTTP layer — anything that
can reach its bound address can drive the Windows box through it. The loopback-only
default (`JOURNEYCAPTURE_MCP_HOST=127.0.0.1`) is what keeps this to "processes on this
machine only." Only change `JOURNEYCAPTURE_MCP_HOST` to a non-loopback address (e.g.
`0.0.0.0`) if you specifically intend to expose it to other machines, and understand
that doing so means unauthenticated remote control of the Windows box for anyone who
can reach that address.

Since VS Code no longer manages this process's lifecycle, restarting it (e.g. after
pulling code changes) is on you — stop it (`Ctrl-C` or `kill`) and run it again.

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
