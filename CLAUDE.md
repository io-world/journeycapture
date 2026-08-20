# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Two components in one repo, meant to run on two different machines:

- **`journeycapture_thinclient`** — a Windows thin client exposing a local REST API
  (FastAPI/uvicorn) for remote mouse/keyboard control and desktop screenshot capture.
  The server code is cross-platform Python, but it's only ever *run* as a packaged
  `.exe` on a real Windows desktop — mouse/keyboard injection (`pynput`) and
  screenshot capture (`mss`) are Windows-only in practice, and the whole point of the
  tool is remote-controlling a Windows machine. Protected by an API-key header and a
  source-IP allowlist, both required in `config.json`.
- **`journeycapture_mcp`** — an MCP server exposing that REST API as MCP tools. Runs
  on the *controller* machine (wherever your MCP client is), not on the Windows box.
  See `docs/MCP_SERVER.md`.

## Commands

```
uv sync                    # install deps for the thin client (creates .venv)
uv sync --extra mcp        # also install deps for the MCP server (controller-side only)
uv run journeycapture      # run the thin client from source (needs config.json - see below)
uv run journeycapture-mcp --config scripts/config.json  # run the MCP server
uv run pytest -q           # run the full test suite
uv run pytest tests/test_security.py::test_wrong_key_raises_401  # run a single test
```

Server config: copy `config.example.json` to `config.json`, set a real `api_key`
(min 16 chars) and non-empty `allowed_ips`. Config path resolution order: `--config
PATH` CLI arg → `JOURNEYCAPTURE_CONFIG` env var → `config.json` next to the executable
(or CWD when run from source). The server refuses to start on a missing/invalid config
(see `journeycapture_thinclient.config.load_config`).

There is no lint/format command configured in this repo.

## Architecture

- **`journeycapture_thinclient.server`** — entry point (`main()`). Loads config, sets up logging,
  calls `winutil.set_dpi_awareness()` (Windows-only, no-op elsewhere), builds the
  FastAPI app, runs it with uvicorn.
- **`journeycapture_thinclient.api.create_app`** — wires a single `Depends` security gate
  (`security.make_verify_request`) onto every route in the app, then mounts the
  routers (`health`, `screenshot`, `mouse`, `keyboard`). There's no per-route auth —
  it's all-or-nothing at the app level.
- **`journeycapture_thinclient.security`** — `verify_request` checks source IP against
  `allowed_ips` *before* checking the API key (403 beats 401 — deliberate, see
  `test_disallowed_ip_checked_before_key`), using `secrets.compare_digest` for the key
  comparison. This gate is wired in as a FastAPI-level `Depends`, which does **not**
  cover `/docs`, `/redoc`, or `/openapi.json` — FastAPI adds those as plain Starlette
  routes outside the dependency-injection path, so they're reachable without the
  API key or an allowlisted IP. Left this way deliberately (verified via `TestClient`)
  so tooling — including an MCP server — can introspect the API shape without
  credentials; only the ability to *act* is gated. There's also no TLS — traffic
  (including the API key itself) is plaintext HTTP, an accepted tradeoff as long as
  the controller and the Windows box share a trusted network; revisit if that stops
  being true.
- **`journeycapture_thinclient.routes/*`** — thin FastAPI route handlers; all actual logic lives
  in `capture.py` (screenshots, via `mss` + Pillow) and `input_control.py`
  (mouse/keyboard, via `pynput`). Routes are mockable at the
  `journeycapture_thinclient.routes.<module>.<capture|input_control>.<fn>` path — that's the
  patching convention `tests/test_api_contract.py` uses throughout.
- **`journeycapture_thinclient.config.Config`** — pydantic model with `extra="forbid"`, so an
  unrecognized config key is a hard validation error, not a silent no-op.
- **`packaging/run.py`** — the PyInstaller entry point (`from journeycapture_thinclient import
  main; main()`), kept as a separate file from `server.py` deliberately for the build.

### Keyboard typing is intentionally paced

`input_control.type_text` sends one character at a time with a small `time.sleep`
between each, rather than a single unpaced `pynput` `.type(text)` call. An unpaced call
was found to silently drop and corrupt characters under load (verified via live
testing against a real Windows box — not reproducible in the mocked test suite), while
still reporting the full length as typed. Don't revert to a single bulk `.type()` call
without re-verifying against a live instance. `\n` in typed text is translated to
`Key.enter` by `pynput` automatically (see `pynput`'s `_CONTROL_CODES`), so no special
handling is needed to end typed text with a return.

### Never assume the screen resolution

`/mouse/move` and `/mouse/click`'s `x`/`y` are real pixel coordinates on the actual
Windows box — there's no scaling or normalization. A caller (human or LLM) that
estimates an icon's position from a screenshot without confirming the image's real
pixel dimensions first will silently compute coordinates for the wrong resolution and
click empty desktop instead. This actually happened: something assumed 1366×768 on a
machine that's really 1920×1080, and every click landed about 29% short of the real
target (`351×(1920/1366)≈493`, the real x for what should have been Chrome's icon).
`GET /screenshot/monitors` and `take_screenshot`'s own response both carry the real
`width`/`height` — always read coordinates from one of those, never assume a
standard resolution. `journeycapture_mcp`'s `list_monitors`/`take_screenshot` tool
docstrings and `screenshot_monitors`'s OpenAPI description both say this explicitly
for the same reason. See `docs/CHANGELOG.md`'s "Fix the actual root cause" entry.

This trap turned out to have a second form even after that fix landed: an MCP client
correctly checked `list_monitors`, then still miscalculated because it reasoned that
the screenshot image "renders smaller in the chat" than its real dimensions and tried
to derive its own scale-factor correction — conflating how big an image *looks* in a
UI with the actual pixel data a model reasons over, which are unrelated. It happened
to land two clicks correctly; there was no way for the model to actually verify the
scale factor it invented, so treat that as luck, not a validated technique. The real
fix, in `journeycapture_mcp.server`: `move_mouse`/`click_mouse` accept `fx`/`fy`
(0.0–1.0, a fraction of the target monitor) as an alternative to pixel `x`/`y`. A
fraction is correct regardless of what size the model actually perceived the image
at — no scale-factor guessing needed, ever. Prefer `fx`/`fy` over `x`/`y` whenever a
target was identified visually from a screenshot. See `docs/MCP_SERVER.md`'s
"Fractional coordinates" section and `docs/CHANGELOG.md`'s corresponding entry.

### Screenshot/pixel control is deliberate, not a limitation to patch

UI Automation (UIA)-based element targeting — asking Windows directly "where is the
button named X" instead of guessing a pixel coordinate from a screenshot — was
considered and explicitly rejected, not overlooked. The design goal is to mimic how
an actual human uses the computer: look at the screen, decide where to click based on
what's visible, act — the same thing a screenshot + pixel coordinates already does.
UIA would be a fundamentally different paradigm (querying a structured accessibility
tree a user never sees), not a refinement of this one.

It was also weighed against real costs, not just philosophy: UIA's `Value` pattern
exposes live text field contents (a privacy leak the `/keyboard/type` audit-logging
carve-out specifically avoids elsewhere), UIA calls can hang against unresponsive
apps, coordinates from a second system would need their own DPI/multi-monitor
correctness verification, and splitting "find" and "click" into two calls reopens a
staleness/TOCTOU window. None of that changes the resolution-assumption bug this
session actually hit — the fix for that is `list_monitors`/reading the screenshot's
real dimensions (see below), which is already in place and doesn't require any of
this. Don't propose UIA-based targeting again without this context.

### Every command is logged; held input auto-releases

Every mouse/keyboard/screenshot route logs one line (endpoint, source IP, and the
relevant params) before acting, via each route module's own `logging.getLogger(__name__)`
— reaches both the console and the rotating log file through the root-logger handlers
`logging_setup.configure_logging` already sets up, so nothing extra is needed to see it.
`/keyboard/type` logs the character *count* only, never the text itself, since that
could be a password or other sensitive content. `/health` is deliberately not logged —
it's a liveness ping, not a remote-control command.

`click_mouse`/`send_keys`'s `action="down"`/`"press"` (holding a button/key across
separate requests, e.g. for a drag) auto-release after `_AUTO_RELEASE_SECONDS` (10s) if
the matching `"up"`/`"release"` never arrives, so a dropped request can't leave input
stuck on the remote machine indefinitely. `action="tap"` (the default, and everything
the test suite and live-testing scripts use) presses and releases within the same call
and never touches this — only an explicit `down`/`press` schedules a timer. See
`tests/test_input_control.py` for how this is tested without waiting on the real timeout.

### Testing against a real Windows instance

Since `pynput`/`mss` behavior and the packaged `.exe` can only be fully verified on
real Windows hardware, `scripts/` holds standalone httpx-based scripts for live
testing, run from any machine that can reach the Windows box (never on the box itself):

- `scripts/live_check.py` — full smoke test: `/health`, wrong-key 401, monitors,
  screenshot, optional `--with-mouse`/`--with-keyboard` round trips.
- `scripts/get_screenshot.py` — fetch one screenshot to a local file.
- `scripts/send_text.py` — type a `TEXT` string (edit the constant at the top of the
  file) into whatever window has focus remotely.
- `scripts/move_mouse.py` — walk the cursor through the primary monitor's corners and
  center plus one relative move, checking the API's reported position against what
  was requested at each step.

All four read connection defaults (`host`, `port`, `api_key`, etc.) from
`scripts/config.json`, which is gitignored (contains the real API key) — there's no
committed example for it, so recreate it locally with the field names each script's
`--help` documents.

Manual-only checks that can't be scripted from macOS (IP-allowlist 403 from a
disallowed source, DPI-scaling coordinate correctness, UIPI/elevated-window behavior,
Firewall/AV prompts) are in `docs/WINDOWS_SMOKE_TEST.md`.

### Building the Windows executable

Must run on real Windows (PyInstaller doesn't cross-compile) — see
`docs/WINDOWS_BUILD.md` for the full manual walkthrough, or run
`scripts/build_windows.ps1` for the one-shot version (installs `uv` if missing, syncs
deps, runs the test suite, builds a version-named `dist/journeycapture-<version>.exe`
via PyInstaller, copies `config.example.json` → `dist/config.json` if missing).

### `journeycapture_mcp` — the MCP server

Lives in `src/journeycapture_mcp/`, a separate top-level package from `journeycapture_thinclient`
in the same repo/pyproject (`[tool.uv.build-backend] module-name` lists both). Its
dependencies (`mcp`, `httpx`) sit under the `mcp` optional-dependency group, not the
base `dependencies` list, specifically so `scripts/build_windows.ps1`'s plain
`uv sync` on the Windows box never needs to know the MCP SDK exists.

- **`config.py`** — `load_settings(config_path=None)`: with a path (the `--config`
  CLI flag), reads a JSON file shaped like `scripts/config.json`; without one, falls
  back to `JOURNEYCAPTURE_HOST`/`_PORT`/`_SCHEME`/`_API_KEY`/`_MCP_HOST`/`_MCP_PORT`
  env vars. Either way it's the Windows box's address (`host`/`port`/`scheme`/
  `api_key`) plus where this server itself listens (`mcp_host`/`mcp_port`, default
  `127.0.0.1:8000` — deliberately separate names from the first pair to avoid
  confusing "the Windows box" with "this server"). Fails fast with a clear stderr
  message if host/api_key are missing either way (mirrors
  `journeycapture_thinclient.config.load_config`'s fail-fast philosophy).
- **`client.py`** — `JourneyCaptureClient`, an async `httpx`-based wrapper around the
  REST API, one method per endpoint. Raises `JourneyCaptureError` on non-2xx
  responses, with the response body included (that's where FastAPI's 422 validation
  details live).
- **`server.py`** — `build_server(client)` builds an `MCPServer`
  (`mcp.server.mcpserver.MCPServer` — this SDK's current name for what used to be
  called `FastMCP`) and registers one `@server.tool()` per REST endpoint, with
  docstrings mirroring the REST API's own OpenAPI descriptions. `take_screenshot`
  returns `mcp.server.mcpserver.Image` (base64-encoded image content), not raw bytes
  or a file path — the one endpoint needing translation rather than a passthrough.
  Parameterized by `client` (rather than importing a module-level singleton) so tests
  can pass an `AsyncMock` and call `server.call_tool(name, args)` directly, in-process,
  with no real network or HTTP transport involved. Every tool logs its name and
  arguments before calling `client` (same privacy carve-out as the thin client's own
  `/keyboard/type` route: `type_text` logs the character count, never the text) — this
  is what to check if something looks wrong, e.g. whether a double-click actually
  arrived as one `clicks=2` call or as two separate single clicks too far apart to
  register as a real double-click on the Windows side.
- **`logging_setup.py`** — same console + rotating-file-handler pattern as
  `journeycapture_thinclient.logging_setup`, writing to `journeycapture-mcp.log` next
  to wherever the command was run from.
- **`__init__.main()`** — the `journeycapture-mcp` console-script entry point: loads
  config, builds the client and server, calls
  `server.run(transport="streamable-http", host=settings.mcp_host, port=settings.mcp_port)`.
  Streamable HTTP, not stdio — the user runs this themselves in a terminal and it
  keeps listening (loopback-only by default) rather than being spawned/owned by the
  MCP client's own lifecycle. This server has no auth of its own at the MCP/HTTP
  layer, so the loopback default is the only thing standing between "just this
  machine" and "unauthenticated remote control of the Windows box" if
  `JOURNEYCAPTURE_MCP_HOST` were ever pointed at a non-loopback address.

Full setup/config/testing details: `docs/MCP_SERVER.md`.
