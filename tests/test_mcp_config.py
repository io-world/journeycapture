from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("mcp")  # controller-side-only extra; not installed for the Windows thin-client build

from journeycapture_mcp.config import ConfigError, load_settings


def write_config(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data))
    return path


def test_loads_from_file(tmp_path: Path) -> None:
    path = write_config(tmp_path, {"host": "192.168.1.50", "api_key": "a" * 32})
    settings = load_settings(path)
    assert settings.host == "192.168.1.50"
    assert settings.api_key == "a" * 32
    assert settings.port == 8443
    assert settings.mcp_host == "127.0.0.1"
    assert settings.mcp_port == 8000


def test_file_overrides_all_fields(tmp_path: Path) -> None:
    path = write_config(
        tmp_path,
        {
            "host": "10.0.0.5",
            "api_key": "b" * 32,
            "port": 9000,
            "scheme": "https",
            "timeout": 5.0,
            "mcp_host": "0.0.0.0",
            "mcp_port": 9001,
        },
    )
    settings = load_settings(path)
    assert settings.port == 9000
    assert settings.scheme == "https"
    assert settings.timeout == 5.0
    assert settings.mcp_host == "0.0.0.0"
    assert settings.mcp_port == 9001


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_settings(tmp_path / "does-not-exist.json")


def test_malformed_json_raises(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text("{not valid json")
    with pytest.raises(ConfigError, match="not valid JSON"):
        load_settings(path)


def test_missing_host_raises(tmp_path: Path) -> None:
    path = write_config(tmp_path, {"api_key": "a" * 32})
    with pytest.raises(ConfigError, match="host"):
        load_settings(path)


def test_missing_api_key_raises(tmp_path: Path) -> None:
    path = write_config(tmp_path, {"host": "192.168.1.50"})
    with pytest.raises(ConfigError, match="api_key"):
        load_settings(path)


def test_env_vars_used_when_no_config_path(monkeypatch) -> None:
    monkeypatch.setenv("JOURNEYCAPTURE_HOST", "192.168.1.50")
    monkeypatch.setenv("JOURNEYCAPTURE_API_KEY", "a" * 32)
    settings = load_settings()
    assert settings.host == "192.168.1.50"


def test_missing_host_env_var_raises(monkeypatch) -> None:
    monkeypatch.delenv("JOURNEYCAPTURE_HOST", raising=False)
    monkeypatch.delenv("JOURNEYCAPTURE_API_KEY", raising=False)
    with pytest.raises(ConfigError, match="JOURNEYCAPTURE_HOST"):
        load_settings()
