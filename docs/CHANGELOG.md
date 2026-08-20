# Changelog

Notable changes to JourneyCapture, newest first. Commit hashes refer to `main`.

## 2026-08-19 — Cap and prune saved screenshots

Found during a broader "what else should I know about" audit: `save_screenshots`
wrote a new file on every `take_screenshot` call with nothing ever removing one,
unlike `journeycapture.log`/`journeycapture-mcp.log` which both rotate. Left running,
`screenshot_dir` would grow forever.

- New `Settings.max_saved_screenshots` (default `100`), configurable via
  `scripts/config.json`-style file key or `JOURNEYCAPTURE_MCP_MAX_SAVED_SCREENSHOTS`
  env var. `0` or negative disables pruning (keep everything).
- After each save, oldest files beyond the cap are deleted (sorted by filename, which
  is already chronological since it's a UTC timestamp) — a count-based cap, simpler
  and more predictable than a size- or age-based one given how much screenshot file
  size varies. A prune failure logs a warning, same as a save failure, and never
  breaks the underlying `take_screenshot` call.
- Verified live against the real Windows box: capped at 3, called 5 times, exactly
  the 3 newest files remained (2 prune events logged as expected).
- 2 new tests — 65 tests total, up from 63.

## 2026-08-19 — Unify get_screenshot.py's output with screenshot_dir

`get_screenshot.py`'s `output_file` config key (a single fixed filename, always
overwritten) was redundant now that `scripts/config.json` already has
`screenshot_dir` from the MCP server's local-saving feature added just before this.
Removed `output_file`; the script now saves into `screenshot_dir` with a timestamped
filename (matching `journeycapture_mcp/server.py`'s `_save_screenshot` naming format
exactly), so manually-fetched screenshots and MCP-auto-saved ones land in one shared
folder instead of two different places with two different config keys. `--out` still
works as a CLI-only exact-path override for one-off cases; `--dir` is new for
overriding just the directory. Verified live against the real Windows box, including
the `--out` override path.

## 2026-08-19 — Optional local screenshot saving in the MCP server

`take_screenshot` can now also save a timestamped copy locally, for debugging what a
model actually saw (relevant given the resolution/scaling issues found earlier this
session). Off by default, enabled for this setup right now.

- New `Settings` fields `save_screenshots` (default `False`) and `screenshot_dir`
  (default `"screenshots"`), configurable via `scripts/config.json`-style file keys
  or `JOURNEYCAPTURE_MCP_SAVE_SCREENSHOTS`/`JOURNEYCAPTURE_MCP_SCREENSHOT_DIR` env
  vars.
- `build_server` now takes `settings` alongside `client` (signature change — the
  `server` fixture in `tests/test_mcp_server.py` updated to match).
- Filenames are UTC timestamps to the microsecond, so rapid/concurrent screenshots
  don't collide. A save failure logs a warning but doesn't fail the underlying
  `take_screenshot` call — it's a debugging convenience, not core functionality.
- `screenshots/` is gitignored. Enabled locally via `scripts/config.json`
  (gitignored itself, not part of this commit) for this session's setup.
- 2 new tests (default-off, saves-when-enabled) — 63 tests total, up from 61.
  Verified live against the real Windows box.

## 2026-08-19 — Add fractional coordinates to the MCP mouse tools

Live use surfaced a second form of the resolution-guessing bug, after the first fix
landed. The model correctly checked `list_monitors` (1920×1080), but then reasoned
that screenshot images "arrive in the chat rendered at a smaller display size
(~1366×768)" and applied its own ~1.406× scale correction to its visual pixel
estimate. It worked — both test clicks landed — but the reasoning doesn't hold up:
how large an image *looks* in a chat UI is unrelated to the actual pixel data a
vision model reasons over. Confirmed nothing in this codebase resizes the screenshot
(`capture.py` returns the raw `mss` capture untouched); if a resize is happening at
all, it's inside Anthropic's own vision preprocessing, which the model has no way to
actually verify. Treated the two successful clicks as luck, not a validated
technique, since the same failure shape (assumed number, no way to confirm it) was
already what caused the original bug.

- `journeycapture_mcp.server`'s `move_mouse` and `click_mouse` tools now accept
  `fx`/`fy` (0.0–1.0, a fraction of the target monitor's width/height) as an
  alternative to pixel `x`/`y`, plus `monitor` to pick which monitor they're relative
  to. Resolved server-side via a new `_resolve_xy` helper that calls
  `list_monitors()` and does the fraction→pixel math — a fraction is correct
  regardless of what size the model actually perceived the screenshot at, no
  scale-factor guessing required. Mutually exclusive with `x`/`y` per call; can't be
  combined with `move_mouse`'s `relative=True`.
- Scoped to the MCP layer only, not the REST API — avoids another Windows exe
  rebuild/republish for a controller-side ergonomics fix, and mirrors the existing
  layering where the MCP layer already translates things (e.g. `take_screenshot`
  returning `Image` content).
- 6 new tests in `tests/test_mcp_server.py` (conversion math, monitor selection, all
  three validation-error cases) — 61 tests total, up from 55. Verified live against
  the real Windows box: `fx=0.2568, fy=0.1213` resolved to `(493, 131)`, the same
  pixel position independently verified correct earlier this session.
- `CLAUDE.md`'s "Never assume the screen resolution" section and
  `docs/MCP_SERVER.md` both updated with the fix and this incident.

## 2026-08-19 — Design decision: no UIA, screenshots stay primary

Follow-up discussion after the coordinate/resolution bug: considered adding Windows
UI Automation (UIA)-based element targeting — finding a button/icon by name via the
accessibility tree instead of guessing pixel coordinates from a screenshot. Decided
against it. Documented in `CLAUDE.md` ("Screenshot/pixel control is deliberate, not a
limitation to patch") so it isn't proposed again as an oversight:

- The product goal is mimicking how an actual human uses the computer — look at the
  screen, click what's visible — which screenshots already do. UIA queries a
  structured tree a user never sees; it's a different paradigm, not a refinement.
- Real costs were weighed too, not just philosophy: UIA's `Value` pattern would leak
  live text field contents (undoing the privacy carve-out `/keyboard/type` already
  has), UIA calls can hang, a second coordinate system needs its own correctness
  verification, and splitting "find" from "click" into two calls reopens a staleness
  window — none of which the actual bug (an assumed resolution) required solving.
- No code changes — this is a documented decision, not a build.

## 2026-08-19 — Fix the actual root cause: coordinates computed against the wrong resolution

Follow-up to the double-click investigation above: a double-click on Chrome's desktop
icon "still didn't work." The actual cause wasn't the click path at all (already
verified working) — it was coordinates computed assuming a 1366×768 screen against a
machine that's really 1920×1080. `351×(1920/1366)≈493`, `104×(1080/768)≈146` — the
failed coordinates were a wrong-resolution-scaled version of Chrome's real icon
position, so every click landed on empty desktop.

- Re-opened Chrome live using the already-verified-correct coordinates from
  `click_test.py`'s earlier run.
- Added an explicit warning to the docstrings most likely to be read right before
  computing coordinates — `journeycapture_mcp/server.py`'s `list_monitors`/
  `take_screenshot` tools and `journeycapture_thinclient/routes/screenshot.py`'s
  `screenshot_monitors` route — to always read the real width/height from the
  response rather than assuming a resolution.
- New `CLAUDE.md` section ("Never assume the screen resolution") documenting this
  failure mode directly, with the exact math that confirmed it.

## 2026-08-19 — MCP server: log every tool call; add click/double-click test script

Prompted by a suspected double-click issue: live-tested it directly against the real
Windows box (new `scripts/click_test.py`) and a single `clicks=2` request worked
correctly on the first try — no bug found in the click path itself. But there was no
way to check what actually got sent to the MCP server in the first place, so the
likely real explanation (two separate single-click calls arriving too far apart to
register as an OS-level double-click, rather than one `clicks=2` call) couldn't be
confirmed either way.

- `journeycapture_mcp` now logs every tool call (name + arguments) before executing
  it, to both console and a new rotating `journeycapture-mcp.log` file
  (`logging_setup.py`, same pattern as the thin client's own). `type_text` logs the
  character count only, never the typed text. This is what to check next time
  something looks off — e.g. whether a click arrived as one `clicks=2` call or two
  separate ones.
- Added `scripts/click_test.py`: single-clicks then double-clicks a target point
  (default: the Chrome desktop icon), saving before/after screenshots so the
  select-vs-launch difference can be checked visually.
- Added 2 tests to `tests/test_mcp_server.py` for the new logging behavior — 55
  tests total, up from 53.

## 2026-08-19 — MCP server: --config file, no more required env vars

`journeycapture_mcp/config.py`'s `load_settings()` now accepts an optional
`config_path`; `journeycapture-mcp --config scripts/config.json` reads host/api_key
straight from the same file the live-testing scripts already use, so there's nothing
to export by hand. Recognizes the same key names (`host`, `api_key`, `port`,
`scheme`, `timeout`) plus two new optional ones (`mcp_host`, `mcp_port`) for
overriding this server's own bind address from the file too. The
`JOURNEYCAPTURE_*` environment variables still work exactly as before — they're the
fallback when `--config` isn't given, not replaced by it. Added `tests/test_mcp_config.py`
(8 tests, previously untested) covering both paths — 53 tests total, up from 45.

## 2026-08-19 — Rename thin client package; switch MCP server to HTTP transport

Two changes:

- Renamed `src/journeycapture/` to `src/journeycapture_thinclient/` (all internal
  imports, test mock-patch targets, and `CLAUDE.md` updated to match), to disambiguate
  it from `journeycapture_mcp` now that both packages live in this repo. Scoped to the
  importable package only — the distribution name, the `journeycapture` CLI command,
  the built exe name, and the log filename default are all unchanged.
- `journeycapture_mcp` now speaks **streamable HTTP** instead of stdio. Previously the
  MCP client (VS Code) launched and owned the process automatically; the desired
  workflow instead was starting `journeycapture-mcp` by hand and pointing `.mcp.json`
  at it, which stdio can't do — there's no "already running" state to point at with
  stdio. Binds `127.0.0.1:8000` by default (new `JOURNEYCAPTURE_MCP_HOST`/
  `_MCP_PORT` env vars, deliberately separate from `JOURNEYCAPTURE_HOST`/`_PORT`,
  which mean the Windows box's address, not this server's own). Loopback-only by
  default is a deliberate mitigation, not an accident: this server holds the real
  thin-client API key internally and has no auth of its own at the MCP/HTTP layer, so
  whatever can reach its bound address can drive the Windows box through it — verified
  the SDK (`mcp==2.0.0`) already defaults `run_streamable_http_async` to
  `127.0.0.1` before relying on it. `.mcp.json` updated from a `command`/`env` stdio
  entry to a `type: "http"` / `url` entry.

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
