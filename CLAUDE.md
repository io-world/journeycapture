# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Windows thin client (`journeycapture`) exposing a local REST API (FastAPI/uvicorn) for
remote mouse/keyboard control and desktop screenshot capture. The server code is
cross-platform Python, but it's only ever *run* as a packaged `.exe` on a real Windows
desktop — mouse/keyboard injection (`pynput`) and screenshot capture (`mss`) are
Windows-only in practice, and the whole point of the tool is remote-controlling a
Windows machine. Protected by an API-key header and a source-IP allowlist, both
required in `config.json`.

## Commands

```
uv sync                    # install deps (creates .venv)
uv run journeycapture      # run the server from source (needs config.json - see below)
uv run pytest -q           # run the full test suite
uv run pytest tests/test_security.py::test_wrong_key_raises_401  # run a single test
```

Server config: copy `config.example.json` to `config.json`, set a real `api_key`
(min 16 chars) and non-empty `allowed_ips`. Config path resolution order: `--config
PATH` CLI arg → `JOURNEYCAPTURE_CONFIG` env var → `config.json` next to the executable
(or CWD when run from source). The server refuses to start on a missing/invalid config
(see `journeycapture.config.load_config`).

There is no lint/format command configured in this repo.

## Architecture

- **`journeycapture.server`** — entry point (`main()`). Loads config, sets up logging,
  calls `winutil.set_dpi_awareness()` (Windows-only, no-op elsewhere), builds the
  FastAPI app, runs it with uvicorn.
- **`journeycapture.api.create_app`** — wires a single `Depends` security gate
  (`security.make_verify_request`) onto every route in the app, then mounts the
  routers (`health`, `screenshot`, `mouse`, `keyboard`). There's no per-route auth —
  it's all-or-nothing at the app level.
- **`journeycapture.security`** — `verify_request` checks source IP against
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
- **`journeycapture.routes/*`** — thin FastAPI route handlers; all actual logic lives
  in `capture.py` (screenshots, via `mss` + Pillow) and `input_control.py`
  (mouse/keyboard, via `pynput`). Routes are mockable at the
  `journeycapture.routes.<module>.<capture|input_control>.<fn>` path — that's the
  patching convention `tests/test_api_contract.py` uses throughout.
- **`journeycapture.config.Config`** — pydantic model with `extra="forbid"`, so an
  unrecognized config key is a hard validation error, not a silent no-op.
- **`packaging/run.py`** — the PyInstaller entry point (`from journeycapture import
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
