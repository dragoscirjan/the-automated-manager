"""Tests for :mod:`automated_manager.config`."""

from __future__ import annotations

from datetime import timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from automated_manager.config import (
    Settings,
    find_dotenv,
    load_settings,
    resolve_timezone,
)
from automated_manager.errors import ConfigError


def test_find_dotenv_walks_up(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("SLACK_USER_TOKEN=xoxp-1\n", encoding="utf-8")
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    assert find_dotenv(nested) == tmp_path / ".env"


def test_find_dotenv_missing(tmp_path: Path) -> None:
    assert find_dotenv(tmp_path) is None


def test_load_settings_from_dotenv(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "SLACK_USER_TOKEN=xoxp-abc\nLLM_PROVIDER=claude\n", encoding="utf-8"
    )
    settings = load_settings(tmp_path)
    assert settings.slack_user_token == "xoxp-abc"
    assert settings.llm_provider == "claude"


def test_load_settings_missing_token_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SLACK_USER_TOKEN", raising=False)
    with pytest.raises(ConfigError):
        load_settings(tmp_path)


def test_settings_populate_by_name() -> None:
    settings = Settings(_env_file=None, slack_user_token="xoxp-x")  # type: ignore[call-arg]
    assert settings.slack_user_token == "xoxp-x"


def test_resolve_timezone_named() -> None:
    assert resolve_timezone("Europe/Bucharest") == ZoneInfo("Europe/Bucharest")


def test_resolve_timezone_default_is_local() -> None:
    assert resolve_timezone(None) is not None


def test_resolve_timezone_unknown_raises() -> None:
    with pytest.raises(ConfigError):
        resolve_timezone("Not/AZone")


def test_resolve_timezone_utc() -> None:
    assert resolve_timezone("UTC") == ZoneInfo("UTC")
    assert ZoneInfo("UTC").utcoffset(None) == timezone.utc.utcoffset(None)
