from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from journeycapture import input_control
from journeycapture.schemas import (
    KeyboardKeyRequest,
    KeyboardTypeRequest,
    KeyboardTypeResponse,
    StatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/keyboard/type", response_model=KeyboardTypeResponse)
def keyboard_type(body: KeyboardTypeRequest, request: Request) -> KeyboardTypeResponse:
    """Type printable text into whatever window has focus. For non-printable keys (Enter, Tab, Ctrl+C, etc.) use /keyboard/key instead — this endpoint only sends character keystrokes."""
    # Log the length only, never the text itself — it could be a password or
    # anything else sensitive typed into a remote window.
    logger.info("keyboard type %d character(s) from %s", len(body.text), request.client.host if request.client else None)
    length = input_control.type_text(body.text)
    return KeyboardTypeResponse(length=length)


@router.post("/keyboard/key", response_model=StatusResponse)
def keyboard_key(body: KeyboardKeyRequest, request: Request) -> StatusResponse:
    """Send one or more named keys, e.g. special keys or chords like ctrl+c that /keyboard/type can't express."""
    logger.info(
        "keyboard key %s action=%s from %s", body.keys, body.action, request.client.host if request.client else None
    )
    try:
        input_control.send_keys(body.keys, action=body.action)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return StatusResponse()
