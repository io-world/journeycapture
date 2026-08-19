from __future__ import annotations

from fastapi import APIRouter, HTTPException

from journeycapture import input_control
from journeycapture.schemas import (
    KeyboardKeyRequest,
    KeyboardTypeRequest,
    KeyboardTypeResponse,
    StatusResponse,
)

router = APIRouter()


@router.post("/keyboard/type", response_model=KeyboardTypeResponse)
def keyboard_type(body: KeyboardTypeRequest) -> KeyboardTypeResponse:
    """Type printable text into whatever window has focus. For non-printable keys (Enter, Tab, Ctrl+C, etc.) use /keyboard/key instead — this endpoint only sends character keystrokes."""
    length = input_control.type_text(body.text)
    return KeyboardTypeResponse(length=length)


@router.post("/keyboard/key", response_model=StatusResponse)
def keyboard_key(body: KeyboardKeyRequest) -> StatusResponse:
    """Send one or more named keys, e.g. special keys or chords like ctrl+c that /keyboard/type can't express."""
    try:
        input_control.send_keys(body.keys, action=body.action)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return StatusResponse()
