from __future__ import annotations

import logging

from fastapi import APIRouter, Request

from journeycapture_thinclient import input_control
from journeycapture_thinclient.schemas import (
    MouseClickRequest,
    MouseMoveRequest,
    MouseMoveResponse,
    MouseScrollRequest,
    StatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/mouse/move", response_model=MouseMoveResponse)
def mouse_move(body: MouseMoveRequest, request: Request) -> MouseMoveResponse:
    """Move the cursor to an absolute screen position, or by a relative offset. Returns the resulting position, which you should check against what was requested."""
    logger.info(
        "mouse move to (%d, %d) relative=%s from %s",
        body.x,
        body.y,
        body.relative,
        request.client.host if request.client else None,
    )
    x, y = input_control.move_mouse(body.x, body.y, relative=body.relative)
    return MouseMoveResponse(x=x, y=y)


@router.post("/mouse/click", response_model=StatusResponse)
def mouse_click(body: MouseClickRequest, request: Request) -> StatusResponse:
    """Click a mouse button, optionally moving to x/y first. Use action=down/up (instead of the default click) to hold a button across separate requests, e.g. for a drag."""
    logger.info(
        "mouse %s button=%s clicks=%d x=%s y=%s from %s",
        body.action,
        body.button,
        body.clicks,
        body.x,
        body.y,
        request.client.host if request.client else None,
    )
    input_control.click_mouse(
        button=body.button,
        action=body.action,
        clicks=body.clicks,
        x=body.x,
        y=body.y,
    )
    return StatusResponse()


@router.post("/mouse/scroll", response_model=StatusResponse)
def mouse_scroll(body: MouseScrollRequest, request: Request) -> StatusResponse:
    """Scroll the mouse wheel at the current cursor position, in wheel notches (not pixels)."""
    logger.info("mouse scroll dx=%d dy=%d from %s", body.dx, body.dy, request.client.host if request.client else None)
    input_control.scroll_mouse(dx=body.dx, dy=body.dy)
    return StatusResponse()
