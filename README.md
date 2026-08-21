# JourneyCapture

Remote-controls Windows desktops (mouse, keyboard, screenshots) through three
components:

```
MCP client  --stdio/HTTP-->  MCP server  --HTTP-->  broker  <--WebSocket--  thin client(s)
```

- **Thin client** (`journeycapture`) — runs on each Windows box, drives the mouse/
  keyboard/screenshots there. Connects *out* to the broker; doesn't accept inbound
  connections.
- **Broker** (`journeycapture-broker`) — routes requests to whichever machine they're
  addressed to. One broker can relay to many thin clients at once.
- **MCP server** (`journeycapture-mcp`) — exposes the broker's API as MCP tools for
  an MCP-aware assistant.

Each runs on its own machine (thin client: the Windows box; broker and MCP server:
typically the controller machine, though nothing requires that).

## Running the thin client from source

```
uv sync
cp examples/config.example.json config.json
# edit config.json: set broker_host/machine_id/api_key to match the broker's config
uv run journeycapture
```

Config is loaded from (in order): `--config PATH`, the `JOURNEYCAPTURE_CONFIG` env
var, or `config.json` next to the executable/CWD.

## Building the Windows executable

See [docs/WINDOWS_BUILD.md](docs/WINDOWS_BUILD.md) — must be built on Windows.
Manual verification checklist: [docs/WINDOWS_SMOKE_TEST.md](docs/WINDOWS_SMOKE_TEST.md).

## Broker

Sits between the MCP server and every thin client.

```
uv sync --extra broker
cp examples/config.broker.example.json broker_config.json
# edit broker_config.json: set api_key and a machine_id/api_key pair per thin client
uv run journeycapture-broker --config broker_config.json
```

See [docs/BROKER.md](docs/BROKER.md) for the HTTP API and how routing works.

## MCP server

```
uv sync --extra mcp
uv run journeycapture-mcp --config scripts/config.json
```

See [docs/MCP_SERVER.md](docs/MCP_SERVER.md) for configuration options, the `machine`
parameter every tool takes, and wiring it into an MCP client.

## Dependencies

See [docs/DEPENDENCIES.md](docs/DEPENDENCIES.md) for what each library is used for.

## Changelog

See [docs/CHANGELOG.md](docs/CHANGELOG.md) for notable changes over time.
