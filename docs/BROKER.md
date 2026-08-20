# Broker

`journeycapture-broker` sits between the MCP server and one or more thin clients
(`journeycapture.exe` instances). It's what makes "one MCP server, many machines"
possible: each thin client connects *out* to the broker over a websocket — it doesn't
accept inbound connections at all — so the broker can reach any machine that can
reach it, regardless of NAT/firewalls on the machine's side. The broker exposes an
HTTP API to the MCP server, namespaced by machine id, mirroring the thin client's
original REST shape.

```
MCP server  --HTTP-->  broker  <--WebSocket--  thin client (journeycapture.exe)
                                <--WebSocket--  thin client (another machine)
```

Runs wherever is reachable by both the MCP server and every thin client — today that's
the same controller machine the MCP server runs on, but nothing about the design
requires that.

## Setup

```
uv sync --extra broker
```

Separate step from the plain `uv sync` used for the thin client — same reasoning as
the `mcp` extra: the Windows build doesn't need to know the broker exists.

## Configuration

JSON file or environment variables, same `load_settings(config_path=None)` pattern as
the MCP server.

**File** (`--config PATH`), see `config.broker.example.json`:

```json
{
  "api_key": "long-random-secret-the-mcp-server-uses",
  "machines": {
    "office-pc": "that-machine's-long-random-secret",
    "home-pc": "a-different-long-random-secret"
  },
  "http_port": 8600,
  "ws_port": 8601
}
```

- `api_key` (required) — what the MCP server authenticates with, checked against
  every `/machines/...` HTTP request's `X-API-Key` header. One key for the whole
  broker, not per-machine.
- `machines` (required, at least one entry) — `machine_id: api_key` pairs. Each thin
  client's own `config.json` needs a matching `machine_id`/`api_key` to be accepted
  when it connects. A thin client with an unknown `machine_id` or wrong key is
  rejected at the websocket handshake, not silently ignored.
- `host`/`http_port` (default `0.0.0.0`/`8600`) — where the MCP-facing HTTP API
  listens.
- `ws_host`/`ws_port` (default `0.0.0.0`/`8601`) — where thin clients connect.
- `request_timeout` (default `15.0` seconds) — how long an HTTP call waits for a
  machine to respond before failing with a `504`.

**Environment variables**: `JOURNEYCAPTURE_BROKER_API_KEY`,
`JOURNEYCAPTURE_BROKER_MACHINES` (a JSON object, e.g.
`'{"office-pc": "...", "home-pc": "..."}'`), `JOURNEYCAPTURE_BROKER_HOST`,
`JOURNEYCAPTURE_BROKER_WS_HOST`, `JOURNEYCAPTURE_BROKER_HTTP_PORT`,
`JOURNEYCAPTURE_BROKER_WS_PORT`.

## Running it

```
uv run journeycapture-broker --config broker_config.json
```

Runs the HTTP API and the websocket server concurrently in one process
(`journeycapture_broker/__init__.py`, `asyncio.gather`). Logs to console and a
rotating `journeycapture-broker.log`, same pattern as the other two components.

## HTTP API

All routes require `X-API-Key` matching the broker's own `api_key`.

- `GET /machines` — list currently-connected machine ids.
- `GET /machines/{id}/health`
- `GET /machines/{id}/screenshot/monitors`
- `GET /machines/{id}/screenshot?format=&quality=&monitor=`
- `POST /machines/{id}/mouse/move`, `/mouse/click`, `/mouse/scroll`
- `POST /machines/{id}/keyboard/type`, `/keyboard/key`

Request/response shapes are identical to the thin client's original REST API — the
broker reuses `journeycapture_thinclient.schemas` directly rather than duplicating
them. A request for a machine id that isn't currently connected gets `404`; a machine
that doesn't respond within `request_timeout` gets `504`; an error the thin client
itself reports (e.g. an unknown key name) gets `400`.

## How a request actually gets routed

`journeycapture_broker/registry.py`'s `ConnectionRegistry` is the core of the broker:
it maps `machine_id` → the machine's live websocket connection, and correlates each
outgoing `{"id", "method", "params"}` message with the HTTP call awaiting a response,
by `id` (a `uuid4` generated per call). When the thin client's response arrives on
that connection, the registry resolves the matching `asyncio.Future`, which is what
the HTTP route was `await`-ing.

Screenshots are the one exception to the plain request/response shape: the thin
client sends the JSON metadata response first (`{"content_type": ...}`, no image
data), then a second, **binary** websocket frame with the raw image bytes — no
base64 anywhere. This only works because each connection is processed sequentially
on both ends (the thin client finishes one broker request, including sending both
screenshot frames, before reading the next) — that's what makes "the next frame after
this response" unambiguous without needing to embed a request id inside binary data.

## Testing

`tests/test_broker_config.py`, `tests/test_broker_registry.py`, and
`tests/test_broker_http_api.py` all require the `broker` extra (`fastapi`) and start
with `pytest.importorskip("fastapi")`, same convention as the `mcp` extra's tests.
Run `uv sync --extra broker && uv run pytest -q` to include them. No live thin client
needed — `test_broker_registry.py` drives `ConnectionRegistry` directly with a mocked
websocket, and `test_broker_http_api.py` mocks the registry itself under a real
`TestClient`.

For an actual end-to-end check, run a broker and point a real thin client's
`config.json` at it (matching `machine_id`/`api_key`), then hit
`GET /machines/{id}/health` through the broker directly, or use
`scripts/live_check.py` (see `CLAUDE.md`) once it's updated to go through the broker.
