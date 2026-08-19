# Dependencies

What each library in `pyproject.toml` is actually used for. Versions are lower
bounds (`>=`); see `uv.lock` for exact resolved versions.

## Thin client (`journeycapture_thinclient`) — base `dependencies`

Runs on the Windows box. `scripts/build_windows.ps1`'s plain `uv sync` installs only
this group — nothing below it.

| Library | Used for |
|---|---|
| `fastapi` | The REST API itself — routing, request/response validation (`src/journeycapture_thinclient/routes/*.py`, `api.py`). |
| `pydantic` | Not listed directly (comes in via `fastapi`), but used explicitly throughout — `schemas.py`'s request/response models and `config.py`'s `Config` validation both subclass `pydantic.BaseModel`. |
| `uvicorn[standard]` | The ASGI server that actually runs the FastAPI app (`server.py`'s `uvicorn.run(...)`). The `[standard]` extra pulls in `uvloop`/`httptools` for performance. |
| `mss` | Cross-platform screenshot capture — grabs raw monitor pixels (`capture.py`'s `list_monitors`/`take_screenshot`). |
| `pillow` | Encodes `mss`'s raw pixel data to JPEG (`capture.py`); PNG output uses `mss`'s own encoder instead. |
| `pynput` | Synthesizes mouse/keyboard input at the OS level (`input_control.py`) — this is what actually moves the cursor, clicks, and types. |

## MCP server (`journeycapture_mcp`) — `mcp` optional-dependency group

Controller-side only. Install with `uv sync --extra mcp`; see `docs/MCP_SERVER.md`.

| Library | Used for |
|---|---|
| `mcp` | The official MCP Python SDK — `MCPServer`/`Image` (`server.py`) build the actual MCP tool server and its streamable-HTTP transport. |
| `httpx` | `client.py`'s `JourneyCaptureClient` — an async HTTP client that calls the thin client's REST API over the network. |

## Dev tooling — `dependency-groups.dev`

Not needed to run either component, only to develop/test/build them. Installed by
default whenever `uv sync` runs (with or without `--extra mcp`).

| Library | Used for |
|---|---|
| `pytest` | The test suite (`tests/`). |
| `pytest-asyncio` | Enables `async def test_*` functions — needed for `journeycapture_mcp`'s async tool/client tests. |
| `httpx` | Also here (not just the `mcp` extra) because `fastapi.testclient.TestClient` is built on it, and the live-testing `scripts/*.py` use it directly. |
| `pyinstaller` | Packages `journeycapture_thinclient` into the standalone Windows `.exe` (`scripts/build_windows.ps1`, `docs/WINDOWS_BUILD.md`). |

## Build backend

`uv_build` (declared in `[build-system]`) — not a dependency of the code itself, it's
what `uv` uses to build/install this project. `[tool.uv.build-backend].module-name`
explicitly lists both `journeycapture_thinclient` and `journeycapture_mcp` since
this repo has two top-level packages under one `pyproject.toml`.
