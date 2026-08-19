from __future__ import annotations

from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from journeycapture.config import Config
from journeycapture.security import make_verify_request


def make_request(host: str) -> Mock:
    request = Mock()
    request.client.host = host
    return request


@pytest.fixture
def config() -> Config:
    return Config(api_key="a" * 32, allowed_ips=["1.2.3.4"])


def test_valid_key_and_allowed_ip_passes(config: Config) -> None:
    verify = make_verify_request(config)
    verify(make_request("1.2.3.4"), x_api_key="a" * 32)


def test_wrong_key_raises_401(config: Config) -> None:
    verify = make_verify_request(config)
    with pytest.raises(HTTPException) as exc_info:
        verify(make_request("1.2.3.4"), x_api_key="wrong-key-wrong-key-wrong-key-12")
    assert exc_info.value.status_code == 401


def test_missing_key_raises_401(config: Config) -> None:
    verify = make_verify_request(config)
    with pytest.raises(HTTPException) as exc_info:
        verify(make_request("1.2.3.4"), x_api_key=None)
    assert exc_info.value.status_code == 401


def test_disallowed_ip_raises_403(config: Config) -> None:
    verify = make_verify_request(config)
    with pytest.raises(HTTPException) as exc_info:
        verify(make_request("9.9.9.9"), x_api_key="a" * 32)
    assert exc_info.value.status_code == 403


def test_disallowed_ip_checked_before_key(config: Config) -> None:
    verify = make_verify_request(config)
    with pytest.raises(HTTPException) as exc_info:
        verify(make_request("9.9.9.9"), x_api_key=None)
    assert exc_info.value.status_code == 403
