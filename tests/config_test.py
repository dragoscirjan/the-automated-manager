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
        (
            "SLACK_USER_TOKEN=xoxp-abc\n"
            "DISCORD_BOT_TOKEN=discord-abc\n"
            "LLM_PROVIDER=claude\n"
        ),
        encoding="utf-8",
    )
    settings = load_settings(tmp_path)
    assert settings.slack_user_token == "xoxp-abc"
    assert settings.discord_bot_token == "discord-abc"
    assert settings.llm_provider == "claude"


def test_load_settings_missing_tokens_allowed_for_command_specific_checks(
    tmp_path: Path,
) -> None:
    settings = load_settings(tmp_path)
    assert settings.slack_user_token is None
    assert settings.discord_bot_token is None


def test_settings_populate_by_name() -> None:
    settings = Settings(  # type: ignore[call-arg]
        _env_file=None,
        slack_user_token="xoxp-x",
        discord_bot_token="discord-x",
    )
    assert settings.slack_user_token == "xoxp-x"
    assert settings.discord_bot_token == "discord-x"


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
