# JourneyCapture

A thin client for Windows that exposes a local REST API to remote-control the mouse
and keyboard and capture desktop screenshots. Protected by an API-key check and an
IP allowlist, both configured via `config.json`.

## Running from source

```
uv sync
cp config.example.json config.json
# edit config.json: set a real api_key and your controller's allowed_ips
uv run journeycapture
```

## Configuration

See `config.example.json`. Config is loaded from (in order): `--config PATH`, the
`JOURNEYCAPTURE_CONFIG` env var, or `config.json` next to the executable/CWD.

## API

All routes require an `X-API-Key` header and a source IP present in `allowed_ips`.

- `GET /health`
- `GET /screenshot/monitors`
- `GET /screenshot?format=&quality=&monitor=`
- `POST /mouse/move`, `/mouse/click`, `/mouse/scroll`
- `POST /keyboard/type`, `/keyboard/key`

## Building the Windows executable

See [docs/WINDOWS_BUILD.md](docs/WINDOWS_BUILD.md) — must be built on Windows.
Manual verification checklist: [docs/WINDOWS_SMOKE_TEST.md](docs/WINDOWS_SMOKE_TEST.md).

## MCP server

An MCP server exposing this API as tools for MCP-aware assistants — runs on the
controller machine, separately from `journeycapture.exe`. See
[docs/MCP_SERVER.md](docs/MCP_SERVER.md).

## Changelog

See [docs/CHANGELOG.md](docs/CHANGELOG.md) for notable changes over time.
