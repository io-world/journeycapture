from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

pytest.importorskip("mcp")  # controller-side-only extra; not installed for the Windows thin-client build

from journeycapture_mcp.server import build_server


@pytest.fixture
def client() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def server(client: AsyncMock):
    return build_server(client)


@pytest.mark.asyncio
async def test_health_check_calls_client(server, client: AsyncMock) -> None:
    client.health.return_value = {"status": "ok", "version": "0.1.0"}
    result = await server.call_tool("health_check", {})
    client.health.assert_called_once_with()
    assert not result.is_error


@pytest.mark.asyncio
async def test_move_mouse_passes_through_args(server, client: AsyncMock) -> None:
    client.move_mouse.return_value = {"status": "ok", "x": 5, "y": 6}
    await server.call_tool("move_mouse", {"x": 5, "y": 6, "relative": True})
    client.move_mouse.assert_called_once_with(5, 6, relative=True)


@pytest.mark.asyncio
async def test_click_mouse_passes_through_args(server, client: AsyncMock) -> None:
    client.click_mouse.return_value = {"status": "ok"}
    await server.call_tool("click_mouse", {"button": "right", "action": "down"})
    client.click_mouse.assert_called_once_with(button="right", action="down", clicks=1, x=None, y=None)


@pytest.mark.asyncio
async def test_type_text_passes_through_text(server, client: AsyncMock) -> None:
    client.type_text.return_value = {"status": "ok", "length": 5}
    await server.call_tool("type_text", {"text": "hello"})
    client.type_text.assert_called_once_with("hello")


@pytest.mark.asyncio
async def test_type_text_logs_length_not_text(server, client: AsyncMock, caplog) -> None:
    secret = "s3cr3t-password"
    client.type_text.return_value = {"status": "ok", "length": len(secret)}
    with caplog.at_level(logging.INFO, logger="journeycapture_mcp.server"):
        await server.call_tool("type_text", {"text": secret})
    assert secret not in caplog.text
    assert f"{len(secret)} character" in caplog.text


@pytest.mark.asyncio
async def test_click_mouse_logs_call(server, client: AsyncMock, caplog) -> None:
    client.click_mouse.return_value = {"status": "ok"}
    with caplog.at_level(logging.INFO, logger="journeycapture_mcp.server"):
        await server.call_tool("click_mouse", {"clicks": 2, "x": 100, "y": 200})
    assert "click_mouse" in caplog.text
    assert "clicks=2" in caplog.text


@pytest.mark.asyncio
async def test_send_keys_passes_through_args(server, client: AsyncMock) -> None:
    client.send_keys.return_value = {"status": "ok"}
    await server.call_tool("send_keys", {"keys": ["ctrl", "c"], "action": "tap"})
    client.send_keys.assert_called_once_with(["ctrl", "c"], action="tap")


@pytest.mark.asyncio
async def test_take_screenshot_returns_image_content(server, client: AsyncMock) -> None:
    client.screenshot.return_value = (b"fake-jpeg-bytes", "image/jpeg")
    result = await server.call_tool("take_screenshot", {})
    assert not result.is_error
    assert result.content[0].type == "image"
    assert result.content[0].mime_type == "image/jpeg"


@pytest.mark.asyncio
async def test_list_monitors_calls_client(server, client: AsyncMock) -> None:
    client.list_monitors.return_value = [{"index": 0, "left": 0, "top": 0, "width": 1920, "height": 1080}]
    result = await server.call_tool("list_monitors", {})
    client.list_monitors.assert_called_once_with()
    assert not result.is_error
