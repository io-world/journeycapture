from __future__ import annotations

import logging
from unittest.mock import patch

from fastapi.testclient import TestClient

from journeycapture.schemas import MonitorInfo


def test_health_requires_auth(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 401


def test_health_ok(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/health", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_disallowed_ip_rejected(config, auth_headers: dict[str, str]) -> None:
    from journeycapture.api import create_app

    app = create_app(config)
    with TestClient(app, client=("9.9.9.9", 12345)) as other_client:
        response = other_client.get("/health", headers=auth_headers)
    assert response.status_code == 403


def test_screenshot_monitors(client: TestClient, auth_headers: dict[str, str]) -> None:
    fake_monitors = [MonitorInfo(index=0, left=0, top=0, width=1920, height=1080)]
    with patch("journeycapture.routes.screenshot.capture.list_monitors", return_value=fake_monitors):
        response = client.get("/screenshot/monitors", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == [m.model_dump() for m in fake_monitors]


def test_screenshot(client: TestClient, auth_headers: dict[str, str]) -> None:
    with patch(
        "journeycapture.routes.screenshot.capture.take_screenshot",
        return_value=(b"fake-image-bytes", "image/jpeg"),
    ):
        response = client.get("/screenshot", headers=auth_headers)
    assert response.status_code == 200
    assert response.content == b"fake-image-bytes"
    assert response.headers["content-type"] == "image/jpeg"


def test_mouse_move(client: TestClient, auth_headers: dict[str, str]) -> None:
    with patch("journeycapture.routes.mouse.input_control.move_mouse", return_value=(10, 20)):
        response = client.post("/mouse/move", json={"x": 10, "y": 20}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "x": 10, "y": 20}


def test_mouse_move_invalid_body(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post("/mouse/move", json={"x": "not-an-int"}, headers=auth_headers)
    assert response.status_code == 422


def test_mouse_click(client: TestClient, auth_headers: dict[str, str]) -> None:
    with patch("journeycapture.routes.mouse.input_control.click_mouse") as mock_click:
        response = client.post("/mouse/click", json={"button": "left"}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_click.assert_called_once()


def test_mouse_scroll(client: TestClient, auth_headers: dict[str, str]) -> None:
    with patch("journeycapture.routes.mouse.input_control.scroll_mouse") as mock_scroll:
        response = client.post("/mouse/scroll", json={"dx": 1, "dy": -1}, headers=auth_headers)
    assert response.status_code == 200
    mock_scroll.assert_called_once_with(dx=1, dy=-1)


def test_mouse_scroll_out_of_range(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post("/mouse/scroll", json={"dy": 1000}, headers=auth_headers)
    assert response.status_code == 422


def test_mouse_click_too_many_clicks(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post("/mouse/click", json={"clicks": 100}, headers=auth_headers)
    assert response.status_code == 422


def test_keyboard_type(client: TestClient, auth_headers: dict[str, str]) -> None:
    with patch("journeycapture.routes.keyboard.input_control.type_text", return_value=5):
        response = client.post("/keyboard/type", json={"text": "hello"}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "length": 5}


def test_keyboard_type_logs_length_not_text(client: TestClient, auth_headers: dict[str, str], caplog) -> None:
    secret = "s3cr3t-password"
    with caplog.at_level(logging.INFO, logger="journeycapture.routes.keyboard"):
        with patch("journeycapture.routes.keyboard.input_control.type_text", return_value=len(secret)):
            response = client.post("/keyboard/type", json={"text": secret}, headers=auth_headers)
    assert response.status_code == 200
    assert secret not in caplog.text
    assert f"{len(secret)} character" in caplog.text


def test_keyboard_type_too_long(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post("/keyboard/type", json={"text": "a" * 4001}, headers=auth_headers)
    assert response.status_code == 422


def test_keyboard_key(client: TestClient, auth_headers: dict[str, str]) -> None:
    with patch("journeycapture.routes.keyboard.input_control.send_keys") as mock_send:
        response = client.post(
            "/keyboard/key", json={"keys": ["ctrl", "alt", "delete"]}, headers=auth_headers
        )
    assert response.status_code == 200
    mock_send.assert_called_once_with(["ctrl", "alt", "delete"], action="tap")


def test_keyboard_key_invalid_key(client: TestClient, auth_headers: dict[str, str]) -> None:
    with patch(
        "journeycapture.routes.keyboard.input_control.send_keys",
        side_effect=ValueError("unknown key: 'bogus'"),
    ):
        response = client.post("/keyboard/key", json={"keys": ["bogus"]}, headers=auth_headers)
    assert response.status_code == 400
