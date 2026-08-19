from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class MonitorInfo(BaseModel):
    index: int
    left: int
    top: int
    width: int
    height: int


class StatusResponse(BaseModel):
    status: Literal["ok"] = "ok"


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    version: str


class MouseMoveRequest(BaseModel):
    x: int
    y: int
    relative: bool = False


class MouseMoveResponse(StatusResponse):
    x: int
    y: int


class MouseClickRequest(BaseModel):
    button: Literal["left", "right", "middle"] = "left"
    action: Literal["click", "down", "up"] = "click"
    clicks: int = 1
    x: int | None = None
    y: int | None = None


class MouseScrollRequest(BaseModel):
    dx: int = 0
    dy: int = 0


class KeyboardTypeRequest(BaseModel):
    text: str


class KeyboardTypeResponse(StatusResponse):
    length: int


class KeyboardKeyRequest(BaseModel):
    keys: list[str]
    action: Literal["press", "release", "tap"] = "tap"
