from __future__ import annotations

import json
import logging
import secrets

import websockets
from websockets.asyncio.server import ServerConnection, serve

from journeycapture_broker.config import Settings
from journeycapture_broker.registry import ConnectionRegistry

logger = logging.getLogger(__name__)


def _make_handler(settings: Settings, registry: ConnectionRegistry):
    async def handler(websocket: ServerConnection) -> None:
        try:
            handshake_raw = await websocket.recv()
        except websockets.exceptions.ConnectionClosed:
            return

        try:
            handshake = json.loads(handshake_raw)
        except (json.JSONDecodeError, TypeError):
            await websocket.send(json.dumps({"ok": False, "error": "handshake must be a JSON object"}))
            await websocket.close()
            return

        machine_id = handshake.get("machine_id")
        api_key = handshake.get("api_key")
        expected_key = settings.machines.get(machine_id) if isinstance(machine_id, str) else None
        if (
            expected_key is None
            or not isinstance(api_key, str)
            or not secrets.compare_digest(api_key, expected_key)
        ):
            logger.warning("rejected connection for machine_id=%r: unknown machine or bad key", machine_id)
            await websocket.send(json.dumps({"ok": False, "error": "unknown machine_id or invalid api_key"}))
            await websocket.close()
            return

        await websocket.send(json.dumps({"ok": True}))
        registry.register(machine_id, websocket)
        try:
            async for raw in websocket:
                if isinstance(raw, bytes):
                    registry.handle_binary_frame(machine_id, websocket, raw)
                    continue
                try:
                    message = json.loads(raw)
                except json.JSONDecodeError:
                    logger.warning("ignoring malformed message from %s: %r", machine_id, raw)
                    continue
                registry.handle_text_frame(machine_id, websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            registry.unregister(machine_id, websocket)

    return handler


async def run(settings: Settings, registry: ConnectionRegistry) -> None:
    handler = _make_handler(settings, registry)
    async with serve(handler, settings.ws_host, settings.ws_port, max_size=None) as server:
        logger.info("websocket server listening on %s:%d", settings.ws_host, settings.ws_port)
        await server.serve_forever()
