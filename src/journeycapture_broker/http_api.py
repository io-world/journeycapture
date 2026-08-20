from __future__ import annotations

import logging
import secrets
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response

from journeycapture_broker.config import Settings
from journeycapture_broker.registry import ConnectionRegistry, MachineError, MachineNotConnected, MachineTimeout
from journeycapture_thinclient.schemas import (
    KeyboardKeyRequest,
    KeyboardTypeRequest,
    KeyboardTypeResponse,
    MonitorInfo,
    MouseClickRequest,
    MouseMoveRequest,
    MouseMoveResponse,
    MouseScrollRequest,
    StatusResponse,
)

logger = logging.getLogger(__name__)


def create_app(settings: Settings, registry: ConnectionRegistry) -> FastAPI:
    def verify_api_key(x_api_key: str | None = Header(None, alias="X-API-Key")) -> None:
        if not x_api_key or not secrets.compare_digest(x_api_key, settings.api_key):
            raise HTTPException(status_code=401, detail="invalid or missing API key")

    # docs_url/redoc_url/openapi_url disabled: FastAPI's app-level `dependencies`
    # doesn't cover these auto-added routes, so leaving them enabled would expose the
    # full API schema with no X-API-Key check — unlike the MCP server (loopback-only
    # by default), this broker's HTTP listener defaults to 0.0.0.0, so that gap would
    # be reachable by default, not just in an unusual deployment.
    app = FastAPI(dependencies=[Depends(verify_api_key)], docs_url=None, redoc_url=None, openapi_url=None)

    async def _call(machine_id: str, method: str, params: dict) -> tuple[dict, bytes | None]:
        try:
            return await registry.call(machine_id, method, params)
        except MachineNotConnected as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except MachineTimeout as e:
            raise HTTPException(status_code=504, detail=str(e)) from e
        except MachineError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    @app.get("/machines")
    def list_machines() -> list[str]:
        """List machine IDs currently connected to this broker."""
        return registry.connected_machines()

    @app.get("/machines/{machine_id}/health")
    async def health(machine_id: str) -> dict:
        result, _ = await _call(machine_id, "health", {})
        return result

    @app.get("/machines/{machine_id}/screenshot/monitors", response_model=list[MonitorInfo])
    async def screenshot_monitors(machine_id: str) -> list[dict]:
        result, _ = await _call(machine_id, "screenshot_monitors", {})
        return result

    @app.get("/machines/{machine_id}/screenshot")
    async def screenshot(
        machine_id: str,
        format: Literal["png", "jpeg"] | None = Query(None),
        quality: int | None = Query(None, ge=1, le=100),
        monitor: int | None = Query(None, ge=0),
    ) -> Response:
        params = {"format": format, "quality": quality, "monitor": monitor}
        result, image_bytes = await _call(machine_id, "screenshot", params)
        return Response(content=image_bytes, media_type=result["content_type"])

    @app.post("/machines/{machine_id}/mouse/move", response_model=MouseMoveResponse)
    async def mouse_move(machine_id: str, body: MouseMoveRequest) -> dict:
        result, _ = await _call(machine_id, "mouse_move", body.model_dump())
        return result

    @app.post("/machines/{machine_id}/mouse/click", response_model=StatusResponse)
    async def mouse_click(machine_id: str, body: MouseClickRequest) -> dict:
        result, _ = await _call(machine_id, "mouse_click", body.model_dump())
        return result

    @app.post("/machines/{machine_id}/mouse/scroll", response_model=StatusResponse)
    async def mouse_scroll(machine_id: str, body: MouseScrollRequest) -> dict:
        result, _ = await _call(machine_id, "mouse_scroll", body.model_dump())
        return result

    @app.post("/machines/{machine_id}/keyboard/type", response_model=KeyboardTypeResponse)
    async def keyboard_type(machine_id: str, body: KeyboardTypeRequest) -> dict:
        result, _ = await _call(machine_id, "keyboard_type", body.model_dump())
        return result

    @app.post("/machines/{machine_id}/keyboard/key", response_model=StatusResponse)
    async def keyboard_key(machine_id: str, body: KeyboardKeyRequest) -> dict:
        result, _ = await _call(machine_id, "keyboard_key", body.model_dump())
        return result

    return app
