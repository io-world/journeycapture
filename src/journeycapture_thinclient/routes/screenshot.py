from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request, Response

from journeycapture_thinclient import capture
from journeycapture_thinclient.schemas import MonitorInfo

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/screenshot/monitors", response_model=list[MonitorInfo])
def screenshot_monitors() -> list[MonitorInfo]:
    """List monitors with pixel bounds in the same coordinate space /mouse/move uses. Index 0 is the bounding box of all monitors combined; physical monitors start at index 1."""
    return capture.list_monitors()


@router.get("/screenshot")
def screenshot(
    request: Request,
    format: Literal["png", "jpeg"] | None = Query(None, description="Image format. Defaults to the server config's screenshot.format."),
    quality: int | None = Query(None, ge=1, le=100, description="JPEG quality 1-100, ignored for png. Defaults to the server config's screenshot.quality."),
    monitor: int | None = Query(None, ge=0, description="Monitor index from GET /screenshot/monitors. Defaults to the server config's screenshot.monitor."),
) -> Response:
    """Capture a screenshot of one monitor and return the raw image bytes. Defaults for format/quality/monitor come from the server's config.json when omitted."""
    config = request.app.state.config
    resolved_format = format or config.screenshot.format
    resolved_quality = quality if quality is not None else config.screenshot.quality
    resolved_monitor = monitor if monitor is not None else config.screenshot.monitor
    logger.info(
        "screenshot monitor=%d format=%s from %s",
        resolved_monitor,
        resolved_format,
        request.client.host if request.client else None,
    )
    try:
        image_bytes, content_type = capture.take_screenshot(
            monitor=resolved_monitor,
            format=resolved_format,
            quality=resolved_quality,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return Response(content=image_bytes, media_type=content_type)
