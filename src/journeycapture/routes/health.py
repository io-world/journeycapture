from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from fastapi import APIRouter

from journeycapture.schemas import HealthResponse

router = APIRouter()

try:
    _VERSION = version("journeycapture")
except PackageNotFoundError:
    _VERSION = "0.0.0"


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(version=_VERSION)
