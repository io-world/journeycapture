from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("fastapi")  # controller-side-only extra; not installed for the Windows thin-client build

from journeycapture_broker.config import ConfigError, load_settings


def write_config(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data))
    return path


def test_loads_from_file(tmp_path: Path) -> None:
    path = write_config(tmp_path, {"api_key": "a" * 32, "machines": {"office-pc": "b" * 32}})
    settings = load_settings(path)
    assert settings.api_key == "a" * 32
    assert settings.machines == {"office-pc": "b" * 32}
    assert settings.http_port == 8600
    assert settings.ws_port == 8601


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_settings(tmp_path / "does-not-exist.json")


def test_missing_api_key_raises(tmp_path: Path) -> None:
    path = write_config(tmp_path, {"machines": {"office-pc": "b" * 32}})
    with pytest.raises(ConfigError, match="api_key"):
        load_settings(path)


def test_missing_machines_raises(tmp_path: Path) -> None:
    path = write_config(tmp_path, {"api_key": "a" * 32})
    with pytest.raises(ConfigError, match="machines"):
        load_settings(path)


def test_env_vars_used_when_no_config_path(monkeypatch) -> None:
    monkeypatch.setenv("JOURNEYCAPTURE_BROKER_API_KEY", "a" * 32)
    monkeypatch.setenv("JOURNEYCAPTURE_BROKER_MACHINES", json.dumps({"office-pc": "b" * 32}))
    settings = load_settings()
    assert settings.api_key == "a" * 32
    assert settings.machines == {"office-pc": "b" * 32}
