from __future__ import annotations

from fastapi import APIRouter

from journeycapture import input_control
from journeycapture.schemas import (
    MouseClickRequest,
    MouseMoveRequest,
    MouseMoveResponse,
    MouseScrollRequest,
    StatusResponse,
)

router = APIRouter()


@router.post("/mouse/move", response_model=MouseMoveResponse)
def mouse_move(body: MouseMoveRequest) -> MouseMoveResponse:
    """Move the cursor to an absolute screen position, or by a relative offset. Returns the resulting position, which you should check against what was requested."""
    x, y = input_control.move_mouse(body.x, body.y, relative=body.relative)
    return MouseMoveResponse(x=x, y=y)


@router.post("/mouse/click", response_model=StatusResponse)
def mouse_click(body: MouseClickRequest) -> StatusResponse:
    """Click a mouse button, optionally moving to x/y first. Use action=down/up (instead of the default click) to hold a button across separate requests, e.g. for a drag."""
    input_control.click_mouse(
        button=body.button,
        action=body.action,
        clicks=body.clicks,
        x=body.x,
        y=body.y,
    )
    return StatusResponse()


@router.post("/mouse/scroll", response_model=StatusResponse)
def mouse_scroll(body: MouseScrollRequest) -> StatusResponse:
    """Scroll the mouse wheel at the current cursor position, in wheel notches (not pixels)."""
    input_control.scroll_mouse(dx=body.dx, dy=body.dy)
    return StatusResponse()
