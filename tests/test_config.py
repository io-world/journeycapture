from __future__ import annotations

import json
from pathlib import Path

import pytest

from journeycapture.config import ConfigError, load_config


def write_config(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data))
    return path


def valid_data() -> dict:
    return {
        "api_key": "a" * 32,
        "allowed_ips": ["192.168.1.50"],
    }


def test_valid_config_parses_with_defaults(tmp_path: Path) -> None:
    path = write_config(tmp_path, valid_data())
    config = load_config(path)
    assert config.host == "0.0.0.0"
    assert config.port == 8443
    assert config.screenshot.format == "jpeg"
    assert config.screenshot.quality == 75
    assert config.log_level == "INFO"


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_config(tmp_path / "does-not-exist.json")


def test_malformed_json_raises(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text("{not valid json")
    with pytest.raises(ConfigError):
        load_config(path)


def test_missing_api_key_raises(tmp_path: Path) -> None:
    data = valid_data()
    del data["api_key"]
    path = write_config(tmp_path, data)
    with pytest.raises(ConfigError):
        load_config(path)


def test_short_api_key_raises(tmp_path: Path) -> None:
    data = valid_data()
    data["api_key"] = "short"
    path = write_config(tmp_path, data)
    with pytest.raises(ConfigError):
        load_config(path)


def test_unknown_field_raises(tmp_path: Path) -> None:
    data = valid_data()
    data["unexpected_field"] = "surprise"
    path = write_config(tmp_path, data)
    with pytest.raises(ConfigError):
        load_config(path)


def test_empty_allowed_ips_raises(tmp_path: Path) -> None:
    data = valid_data()
    data["allowed_ips"] = []
    path = write_config(tmp_path, data)
    with pytest.raises(ConfigError):
        load_config(path)
