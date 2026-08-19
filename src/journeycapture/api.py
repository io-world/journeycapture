from __future__ import annotations

from fastapi import Depends, FastAPI

from journeycapture.config import Config
from journeycapture.routes import health, keyboard, mouse, screenshot
from journeycapture.security import make_verify_request


def create_app(config: Config) -> FastAPI:
    app = FastAPI(dependencies=[Depends(make_verify_request(config))])
    app.state.config = config

    app.include_router(health.router)
    app.include_router(screenshot.router)
    app.include_router(mouse.router)
    app.include_router(keyboard.router)

    return app
