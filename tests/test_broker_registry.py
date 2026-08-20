from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock

import pytest

pytest.importorskip("fastapi")  # controller-side-only extra; not installed for the Windows thin-client build

from journeycapture_broker.config import Settings
from journeycapture_broker.registry import ConnectionRegistry, MachineError, MachineNotConnected, MachineTimeout


@pytest.fixture
def settings() -> Settings:
    return Settings(api_key="a" * 32, machines={"office-pc": "b" * 32}, request_timeout=1.0)


@pytest.mark.asyncio
async def test_call_to_unconnected_machine_raises(settings: Settings) -> None:
    registry = ConnectionRegistry(settings)
    with pytest.raises(MachineNotConnected):
        await registry.call("office-pc", "health", {})


@pytest.mark.asyncio
async def test_call_resolves_with_matching_response(settings: Settings) -> None:
    registry = ConnectionRegistry(settings)
    websocket = AsyncMock()
    registry.register("office-pc", websocket)

    async def respond_soon() -> None:
        await asyncio.sleep(0)
        sent = json.loads(websocket.send.call_args.args[0])
        registry.handle_text_frame("office-pc", {"id": sent["id"], "result": {"status": "ok"}})

    responder = asyncio.create_task(respond_soon())
    result, image = await registry.call("office-pc", "health", {})
    await responder
    assert result == {"status": "ok"}
    assert image is None


@pytest.mark.asyncio
async def test_call_error_response_raises_machine_error(settings: Settings) -> None:
    registry = ConnectionRegistry(settings)
    websocket = AsyncMock()
    registry.register("office-pc", websocket)

    async def respond_soon() -> None:
        await asyncio.sleep(0)
        sent = json.loads(websocket.send.call_args.args[0])
        registry.handle_text_frame("office-pc", {"id": sent["id"], "error": {"message": "boom"}})

    responder = asyncio.create_task(respond_soon())
    with pytest.raises(MachineError, match="boom"):
        await registry.call("office-pc", "keyboard_key", {"keys": ["bogus"]})
    await responder


@pytest.mark.asyncio
async def test_call_times_out() -> None:
    settings = Settings(api_key="a" * 32, machines={"office-pc": "b" * 32}, request_timeout=0.05)
    registry = ConnectionRegistry(settings)
    registry.register("office-pc", AsyncMock())
    with pytest.raises(MachineTimeout):
        await registry.call("office-pc", "health", {})  # nobody ever responds


@pytest.mark.asyncio
async def test_screenshot_waits_for_binary_frame(settings: Settings) -> None:
    registry = ConnectionRegistry(settings)
    websocket = AsyncMock()
    registry.register("office-pc", websocket)

    async def respond_soon() -> None:
        await asyncio.sleep(0)
        sent = json.loads(websocket.send.call_args.args[0])
        registry.handle_text_frame("office-pc", {"id": sent["id"], "result": {"content_type": "image/jpeg"}})
        registry.handle_binary_frame("office-pc", b"fake-jpeg-bytes")

    responder = asyncio.create_task(respond_soon())
    result, image = await registry.call("office-pc", "screenshot", {})
    await responder
    assert result == {"content_type": "image/jpeg"}
    assert image == b"fake-jpeg-bytes"


@pytest.mark.asyncio
async def test_disconnect_fails_pending_calls(settings: Settings) -> None:
    registry = ConnectionRegistry(settings)
    websocket = AsyncMock()
    registry.register("office-pc", websocket)

    async def disconnect_soon() -> None:
        await asyncio.sleep(0)
        registry.unregister("office-pc")

    disconnector = asyncio.create_task(disconnect_soon())
    with pytest.raises(MachineNotConnected):
        await registry.call("office-pc", "health", {})
    await disconnector


def test_connected_machines(settings: Settings) -> None:
    registry = ConnectionRegistry(settings)
    assert registry.connected_machines() == []
    registry.register("office-pc", AsyncMock())
    assert registry.connected_machines() == ["office-pc"]
    registry.unregister("office-pc")
    assert registry.connected_machines() == []
