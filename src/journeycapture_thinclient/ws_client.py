from __future__ import annotations

import asyncio
import json
import logging
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Callable

import websockets
from pydantic import ValidationError
from websockets.asyncio.client import ClientConnection

from journeycapture_thinclient import capture, input_control
from journeycapture_thinclient.config import Config
from journeycapture_thinclient.schemas import (
    KeyboardKeyRequest,
    KeyboardTypeRequest,
    MouseClickRequest,
    MouseMoveRequest,
    MouseScrollRequest,
)

logger = logging.getLogger(__name__)

try:
    _VERSION = version("journeycapture")
except PackageNotFoundError:
    _VERSION = "0.0.0"


class DispatchError(Exception):
    """Raised by a handler for a client-facing error (bad params, unknown key, etc.)."""


class RegistrationRejected(Exception):
    """The broker rejected our machine_id/api_key at the handshake — not recoverable
    by reconnecting, since the credentials themselves are wrong."""


def _handle_health(config: Config, params: dict) -> Any:
    return {"status": "ok", "version": _VERSION}


def _handle_screenshot_monitors(config: Config, params: dict) -> Any:
    return [m.model_dump() for m in capture.list_monitors()]


def _handle_mouse_move(config: Config, params: dict) -> Any:
    body = MouseMoveRequest.model_validate(params)
    x, y = input_control.move_mouse(body.x, body.y, relative=body.relative)
    logger.info("mouse move to (%d, %d) relative=%s", x, y, body.relative)
    return {"status": "ok", "x": x, "y": y}


def _handle_mouse_click(config: Config, params: dict) -> Any:
    body = MouseClickRequest.model_validate(params)
    logger.info("mouse %s button=%s clicks=%d x=%s y=%s", body.action, body.button, body.clicks, body.x, body.y)
    input_control.click_mouse(button=body.button, action=body.action, clicks=body.clicks, x=body.x, y=body.y)
    return {"status": "ok"}


def _handle_mouse_scroll(config: Config, params: dict) -> Any:
    body = MouseScrollRequest.model_validate(params)
    logger.info("mouse scroll dx=%d dy=%d", body.dx, body.dy)
    input_control.scroll_mouse(dx=body.dx, dy=body.dy)
    return {"status": "ok"}


def _handle_keyboard_type(config: Config, params: dict) -> Any:
    body = KeyboardTypeRequest.model_validate(params)
    logger.info("keyboard type %d character(s)", len(body.text))
    length = input_control.type_text(body.text)
    return {"status": "ok", "length": length}


def _handle_keyboard_key(config: Config, params: dict) -> Any:
    body = KeyboardKeyRequest.model_validate(params)
    logger.info("keyboard key %s action=%s", body.keys, body.action)
    try:
        input_control.send_keys(body.keys, action=body.action)
    except ValueError as e:
        raise DispatchError(str(e)) from e
    return {"status": "ok"}


_HANDLERS: dict[str, Callable[[Config, dict], Any]] = {
    "health": _handle_health,
    "screenshot_monitors": _handle_screenshot_monitors,
    "mouse_move": _handle_mouse_move,
    "mouse_click": _handle_mouse_click,
    "mouse_scroll": _handle_mouse_scroll,
    "keyboard_type": _handle_keyboard_type,
    "keyboard_key": _handle_keyboard_key,
}


def _do_screenshot(config: Config, params: dict) -> tuple[bytes, str]:
    fmt = params.get("format") or config.screenshot.format
    quality = params.get("quality") if params.get("quality") is not None else config.screenshot.quality
    monitor = params.get("monitor") if params.get("monitor") is not None else config.screenshot.monitor
    logger.info("screenshot monitor=%d format=%s", monitor, fmt)
    return capture.take_screenshot(monitor=monitor, format=fmt, quality=quality)


async def _handle_screenshot(websocket: ClientConnection, request_id: str, config: Config, params: dict) -> None:
    try:
        image_bytes, content_type = await asyncio.to_thread(_do_screenshot, config, params)
    except ValueError as e:
        await websocket.send(json.dumps({"id": request_id, "error": {"message": str(e)}}))
        return
    # Two frames: JSON metadata first, then the raw image bytes as a binary frame —
    # no base64. Safe because the broker processes one request per connection at a
    # time, so it knows this next frame belongs to this response.
    await websocket.send(json.dumps({"id": request_id, "result": {"content_type": content_type}}))
    await websocket.send(image_bytes)


async def _dispatch(websocket: ClientConnection, config: Config, message: dict) -> None:
    request_id = message.get("id")
    method = message.get("method")
    params = message.get("params") or {}

    if method == "screenshot":
        await _handle_screenshot(websocket, request_id, config, params)
        return

    handler = _HANDLERS.get(method)
    if handler is None:
        await websocket.send(json.dumps({"id": request_id, "error": {"message": f"unknown method: {method!r}"}}))
        return

    try:
        # Runs in a thread — several of these handlers block for real (type_text can
        # take up to ~40s), and blocking the event loop would starve the websocket
        # library's own keepalive pings, risking the broker timing out the connection.
        result = await asyncio.to_thread(handler, config, params)
    except (ValidationError, DispatchError) as e:
        await websocket.send(json.dumps({"id": request_id, "error": {"message": str(e)}}))
        return

    await websocket.send(json.dumps({"id": request_id, "result": result}))


async def run(config: Config) -> None:
    uri = f"ws://{config.broker_host}:{config.broker_port}"
    async for websocket in websockets.connect(uri, max_size=None):
        try:
            await websocket.send(json.dumps({"machine_id": config.machine_id, "api_key": config.api_key}))
            ack = json.loads(await websocket.recv())
            if not ack.get("ok"):
                raise RegistrationRejected(ack.get("error", "broker rejected registration"))

            logger.info("registered with broker %s as machine_id=%s", uri, config.machine_id)

            async for raw in websocket:
                if isinstance(raw, bytes):
                    continue  # the broker never sends us binary frames
                try:
                    message = json.loads(raw)
                except json.JSONDecodeError:
                    logger.warning("ignoring malformed message from broker: %r", raw)
                    continue
                await _dispatch(websocket, config, message)
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning("lost connection to broker (%s), reconnecting...", e)
            continue
