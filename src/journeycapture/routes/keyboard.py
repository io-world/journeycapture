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
    length = input_control.type_text(body.text)
    return KeyboardTypeResponse(length=length)


@router.post("/keyboard/key", response_model=StatusResponse)
def keyboard_key(body: KeyboardKeyRequest) -> StatusResponse:
    try:
        input_control.send_keys(body.keys, action=body.action)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return StatusResponse()
