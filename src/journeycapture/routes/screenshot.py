from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Request, Response

from journeycapture import capture
from journeycapture.schemas import MonitorInfo

router = APIRouter()


@router.get("/screenshot/monitors", response_model=list[MonitorInfo])
def screenshot_monitors() -> list[MonitorInfo]:
    return capture.list_monitors()


@router.get("/screenshot")
def screenshot(
    request: Request,
    format: Literal["png", "jpeg"] | None = None,
    quality: int | None = None,
    monitor: int | None = None,
) -> Response:
    config = request.app.state.config
    resolved_format = format or config.screenshot.format
    resolved_quality = quality if quality is not None else config.screenshot.quality
    resolved_monitor = monitor if monitor is not None else config.screenshot.monitor
    try:
        image_bytes, content_type = capture.take_screenshot(
            monitor=resolved_monitor,
            format=resolved_format,
            quality=resolved_quality,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return Response(content=image_bytes, media_type=content_type)
