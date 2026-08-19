# Changelog

Notable changes to JourneyCapture, newest first. Commit hashes refer to `main`.

## 2026-08-19 — Add the MCP server

New package `src/journeycapture_mcp/`, exposing the REST API as MCP tools. Runs on
the controller machine (wherever the MCP client is), separately from
`journeycapture.exe` on the Windows box — the two now genuinely run on different
computers, talking over the same HTTP API `scripts/*.py` already exercised.

- One MCP tool per REST endpoint (`health_check`, `list_monitors`, `take_screenshot`,
  `move_mouse`, `click_mouse`, `scroll_mouse`, `type_text`, `send_keys`), with
  docstrings mirroring the REST API's own OpenAPI descriptions written in the
  pre-MCP-readiness pass below — same reference info, one layer removed.
  `take_screenshot` returns MCP image content (base64-encoded), the one endpoint
  needing real translation rather than a passthrough.
- Config via environment variables (`JOURNEYCAPTURE_HOST`, `_PORT`, `_SCHEME`,
  `_API_KEY`), read once at startup with a fail-fast error message if host/api_key
  are missing — verified: `journeycapture-mcp` with them unset exits 1 with a clear
  message, not a stack trace.
- New `journeycapture-mcp` terminal command (`[project.scripts]`), speaking MCP over
  stdio — meant to be spawned by an MCP client (Claude Code, Claude Desktop), not run
  interactively.
- The MCP SDK lives behind a new `mcp` optional-dependency group
  (`uv sync --extra mcp`), kept separate from the thin client's own dependencies so
  `scripts/build_windows.ps1`'s plain `uv sync` on the Windows box never needs it.
  The two new test files (`tests/test_mcp_client.py`, `tests/test_mcp_server.py`)
  call `pytest.importorskip("mcp")` so they skip cleanly rather than fail when that
  extra isn't installed — verified by running the full suite both with and without
  `--extra mcp` synced (45 passed vs. 33 passed + 2 skipped).
- New `docs/MCP_SERVER.md` covering setup, configuration, an example `.mcp.json`
  entry, and testing.

## 2026-08-19 — Audit logging + stuck-key safety net

A broader "what concerns you about this build" review turned up two gaps beyond the
pre-MCP pass below:

- **No audit trail.** Every mouse/keyboard/screenshot route now logs one line (via
  each route module's own logger) before acting: endpoint, source IP, and the
  relevant params. Previously the only log line anywhere in the app, ever, was
  "Loaded config from ..." at startup — no record of any command the server had
  received. `/keyboard/type` logs the character count only, never the actual text, so
  a password or other sensitive content typed through it never lands in the log file.
  `/health` stays unlogged (liveness ping, not a command).
- **No recovery from a stuck held key/button.** `/mouse/click` and `/keyboard/key`
  support holding a button/key across separate requests (`action="down"`/`"press"`)
  for things like drags or multi-request chords. If the matching release never
  arrived — dropped request, caller bug — that input stayed held on the Windows
  machine indefinitely, with nothing to notice or fix it. `input_control.py` now
  tracks held buttons/keys and auto-releases them after 10 seconds if no explicit
  release request arrives first, logging a warning when that happens (itself a useful
  signal that some caller dropped a release it should have sent). `action="tap"` (the
  default, and everything used anywhere else in this codebase) is unaffected.
- Added `tests/test_input_control.py` (5 tests) for the auto-release behavior, and a
  test asserting the keyboard-type log line contains the length but never the literal
  text — 33 tests total, up from 27.

## 2026-08-19 — `a1607e8` Pre-MCP API readiness pass

Reviewed the whole API ahead of building an MCP server on top of it and closed three
gaps found in that review:

- **Bounded inputs** (`schemas.py`): `KeyboardTypeRequest.text` capped at 4000 chars,
  `MouseClickRequest.clicks` restricted to 1–10, `MouseScrollRequest.dx`/`dy`
  restricted to ±100. Previously unbounded — combined with the paced `type_text` added
  in the previous change, an oversized `text` could tie up a request for a very long
  time with nothing to stop it.
- **OpenAPI descriptions**: every route got a docstring and the schema fields most
  likely to confuse an API consumer got `Field(description=...)` — coordinate origin
  for `/mouse/move`, wheel-notch units for `/mouse/scroll`, valid key names for
  `/keyboard/key`. Previously every route's OpenAPI `description` was empty.
- **Thread safety** (`input_control.py`): added a `threading.Lock` around all
  `_mouse`/`_keyboard` access. The controllers are module-level singletons and
  FastAPI's sync routes run in a thread pool, so concurrent requests could previously
  interleave mouse/keyboard events unpredictably.
- Added `scripts/move_mouse.py` (see below) and 3 new tests for the new bounds.
- `CLAUDE.md` now records two decisions made in this pass rather than fixed: `/docs`,
  `/redoc`, and `/openapi.json` stay unauthenticated (convenient for schema
  introspection, and they only disclose API shape, not the ability to act), and TLS
  stays out of scope for now (plaintext HTTP is accepted as long as the controller and
  the Windows box share a trusted network).

## 2026-08-19 — `d3f99c6` Add CLAUDE.md, refresh Windows build docs

- Added `CLAUDE.md` — architecture overview, common commands, and the live-testing
  workflow, so a future session has the context this one built up.
- Rewrote `docs/WINDOWS_BUILD.md`: it still described the pre-remote workflow ("copy
  the folder over by USB"); now leads with `git clone` + `scripts/build_windows.ps1`,
  keeping the manual PyInstaller steps only as a fallback for customizing
  `--hidden-import` flags. Added a note that a published release is a frozen artifact —
  pulling new source on the Windows box doesn't update an already-built `.exe`.

## 2026-08-19 — `49fee17` Add Windows build script

- `scripts/build_windows.ps1` (built on the Windows box, in its own Claude Code
  session): one-shot build — installs `uv` if missing, `uv sync`, runs the test suite
  (aborts the build on failure, `-SkipTests` to bypass), builds a version-named
  `dist/journeycapture-<version>.exe` via PyInstaller, copies
  `config.example.json` → `dist/config.json` if one isn't already there.

## 2026-08-19 — `52dec80` Live testing scripts; fix dropped keystrokes

Found via live testing against the real Windows box (`v0.1.0` release): typing a long
string through `/keyboard/type` landed incomplete and corrupted — three separate runs
of the same ~445-character Lorem Ipsum paragraph each dropped a different, random
chunk of text (one run stopped after 15 characters, another lost an entire middle
section, one had a character inserted that was never sent). The API still reported the
full length as typed regardless.

- **Root cause**: `input_control.type_text` called `pynput`'s `Controller.type(text)`
  once, unpaced — sending keydown/keyup events back-to-back with no delay. Under load,
  Windows silently drops or coalesces events from the input queue.
- **Fix**: `type_text` now sends one character at a time with a small
  `time.sleep(interval)` between each (default 10 ms).
- Added three standalone live-testing scripts (run from a controller machine, never on
  the Windows box itself), all reading connection defaults from a gitignored
  `scripts/config.json`:
  - `scripts/live_check.py` — full smoke test: health, wrong-key rejection, monitors,
    screenshot, optional mouse/keyboard round trips.
  - `scripts/get_screenshot.py` — fetch one screenshot to a local file.
  - `scripts/send_text.py` — type a `TEXT` constant (edited directly in the file, so
    it can be run with no arguments, e.g. from VS Code's Run button) into whatever
    window has focus remotely. Confirmed `\n` at the end of `TEXT` is translated to an
    Enter keypress automatically (`pynput`'s `_CONTROL_CODES`).
- Updated `docs/WINDOWS_SMOKE_TEST.md` to point at the new automated checks, keeping
  only what genuinely can't be scripted from macOS (IP-allowlist 403 from a
  disallowed source, DPI-scaling coordinate correctness, UIPI/elevated-window
  behavior, Firewall/AV prompts) as manual steps.

## 2026-08-19 — `7fa331e` Initial version

Windows thin client exposing a local REST API (FastAPI/uvicorn) for remote
mouse/keyboard control and desktop screenshot capture:

- Auth: API-key header + source-IP allowlist, checked on every route via a single
  app-level dependency (IP checked before key — 403 beats 401).
- `GET /health`, `GET /screenshot/monitors`, `GET /screenshot` (via `mss` + Pillow),
  `POST /mouse/move|click|scroll`, `POST /keyboard/type|key` (via `pynput`).
- Config loaded from `config.json` (pydantic, `extra="forbid"`) — real `api_key` and
  non-empty `allowed_ips` required, no insecure defaults.
- Test suite (24 tests) covering config validation, security gate behavior, and API
  contracts via mocked `capture`/`input_control`.
- `docs/WINDOWS_BUILD.md` (manual PyInstaller build walkthrough) and
  `docs/WINDOWS_SMOKE_TEST.md` (manual verification checklist) — both since revised,
  see above.

## Not yet on `main`

Follow-up work discussed but not yet built:
- An MCP server on top of this REST API (the readiness pass above was prep for this;
  the server itself doesn't exist in this repo yet).
- The `v0.1.0` GitHub release predates the keystroke-pacing fix and everything after
  it — a rebuild via `scripts/build_windows.ps1` and a new release are needed before
  any of this reaches a running `.exe`.
