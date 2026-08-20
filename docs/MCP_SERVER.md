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
`8000`), `save_screenshots` (default `false`), `screenshot_dir` (default
`"screenshots"`). Extra keys `scripts/config.json` has for the other scripts
(`monitor`, `format`, `quality`, `out`) are simply ignored.

**Environment variables** (used only when `--config` isn't given):

| Variable | Required | Default | Notes |
|---|---|---|---|
| `JOURNEYCAPTURE_HOST` | yes | — | IP or hostname of the Windows box |
| `JOURNEYCAPTURE_API_KEY` | yes | — | must match `journeycapture.exe`'s `config.json` |
| `JOURNEYCAPTURE_PORT` | no | `8443` | the Windows box's port |
| `JOURNEYCAPTURE_SCHEME` | no | `http` | `http` or `https`, for reaching the Windows box |
| `JOURNEYCAPTURE_MCP_HOST` | no | `127.0.0.1` | where **this** server itself listens |
| `JOURNEYCAPTURE_MCP_PORT` | no | `8000` | where **this** server itself listens |
| `JOURNEYCAPTURE_MCP_SAVE_SCREENSHOTS` | no | off | `1`/`true`/`yes` to enable — see below |
| `JOURNEYCAPTURE_MCP_SCREENSHOT_DIR` | no | `screenshots` | where saved copies go |

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

## Logging

Every tool call is logged (`journeycapture_mcp/server.py`) — tool name and arguments —
to both the console and a rotating `journeycapture-mcp.log` file next to wherever you
ran the command (`journeycapture_mcp/logging_setup.py`, same console+file pattern as
the thin client's own logging). `type_text` logs the character count only, never the
typed text itself, for the same reason the thin client's own `/keyboard/type` route
does — it could be a password or other sensitive content.

This is the log to check if something looks wrong — e.g. to tell whether a
double-click actually arrived as one `click_mouse(clicks=2)` call or as two separate
single clicks close together (which won't register as a real double-click on the
Windows side no matter how close together they are, since each is a fully separate
HTTP round trip).

## Tools

One tool per REST endpoint (`journeycapture_mcp/server.py`) — `health_check`,
`list_monitors`, `take_screenshot`, `move_mouse`, `click_mouse`, `scroll_mouse`,
`type_text`, `send_keys`. Tool descriptions mirror the REST API's own OpenAPI
descriptions (coordinate origin, scroll units, valid key names), so the same
reference in `CLAUDE.md`'s architecture section applies here too.

`take_screenshot` returns MCP image content (base64-encoded), not a file path or raw
bytes — nothing is written to disk on the controller side.

### Fractional coordinates (`fx`/`fy`)

`move_mouse` and `click_mouse` both accept `fx`/`fy` (floats, 0.0–1.0) as an
alternative to pixel `x`/`y` — a fraction of the target monitor's width/height
instead of a raw pixel number. `monitor` picks which monitor they're relative to
(defaults to the primary physical monitor, `list_monitors` index 1).

Use `fx`/`fy` whenever the target was identified visually from a `take_screenshot`
result, instead of estimating a pixel coordinate. This isn't just convenience: a
model has no reliable way to know what resolution an image was actually rendered at
by the time it reasons about it (chat UIs and vision pipelines can both resize images
before/while a model looks at them), so a pixel guess is really a guess about an
unknown scale factor wearing the model's confidence as camouflage. A fraction of the
image is correct regardless of what size the model actually perceived it at — the
server does the real-pixel conversion using `list_monitors`' actual dimensions. See
`CLAUDE.md`'s "Never assume the screen resolution" section for the incident that
prompted this.

`x`/`y` and `fx`/`fy` are mutually exclusive per call (pick one), and `fx`/`fy` can't
be combined with `move_mouse`'s `relative=True` — a fraction of the screen isn't a
meaningful concept for a relative offset.

### Saving screenshots locally

Off by default. Set `save_screenshots: true` (config file) or
`JOURNEYCAPTURE_MCP_SAVE_SCREENSHOTS=1` (env var) to also save a timestamped copy of
every `take_screenshot` result to `screenshot_dir` (default `screenshots/`, created if
missing, relative to wherever `journeycapture-mcp` was run from) — useful for
debugging what the model actually saw. Filenames are UTC timestamps down to the
microsecond (`20260819T235959_123456.jpeg`), so concurrent/rapid screenshots don't
collide. A save failure (disk full, permissions) logs a warning but doesn't fail the
underlying `take_screenshot` call — this is a debugging convenience, not core
functionality. `screenshots/` is gitignored; nothing here is ever committed.

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
