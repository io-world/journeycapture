from __future__ import annotations

import secrets
from typing import Callable

from fastapi import Header, HTTPException, Request

from journeycapture.config import Config


def make_verify_request(config: Config) -> Callable[..., None]:
    def verify_request(
        request: Request,
        x_api_key: str | None = Header(None, alias="X-API-Key"),
    ) -> None:
        client_host = request.client.host if request.client else None
        if client_host not in config.allowed_ips:
            raise HTTPException(status_code=403, detail="source IP not permitted")
        if not x_api_key or not secrets.compare_digest(x_api_key, config.api_key):
            raise HTTPException(status_code=401, detail="invalid or missing API key")

    return verify_request
