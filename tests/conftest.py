from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from journeycapture_thinclient.api import create_app
from journeycapture_thinclient.config import Config

API_KEY = "a" * 32
ALLOWED_IP = "testclient"


@pytest.fixture
def config() -> Config:
    return Config(api_key=API_KEY, allowed_ips=[ALLOWED_IP])


@pytest.fixture
def client(config: Config) -> TestClient:
    app = create_app(config)
    return TestClient(app)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"X-API-Key": API_KEY}
