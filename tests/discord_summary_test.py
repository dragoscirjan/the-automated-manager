"""Tests for :mod:`automated_manager.discord_summary`."""

from __future__ import annotations

from datetime import timezone
from pathlib import Path

import pytest

from automated_manager import discord_summary as discord_summary_mod
from automated_manager.config import Settings
from automated_manager.discord.client import RawConversation, RawMessage
from automated_manager.errors import ConfigError, ValidationError


def _settings(**overrides: object) -> Settings:
    data: dict[str, object] = {"discord_bot_token": "discord-token"}
    data.update(overrides)
    return Settings(_env_file=None, **data)  # type: ignore[call-arg]


@pytest.fixture(autouse=True)
def _patch_collection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        discord_summary_mod, "resolve_timezone", lambda name: timezone.utc
    )

    class _Client:
        def __init__(self, token: str) -> None:
            self._token = token

        def collect(self, period: object, include: set[str]) -> list[RawConversation]:
            return [
                RawConversation(
                    id="D1",
                    title="#eng",
                    kind="guild_text",
                    messages=(
                        RawMessage(ts="1700000000.0", author="alice", text="hi"),
                    ),
                )
            ]

    monkeypatch.setattr(discord_summary_mod, "DiscordClient", _Client)


def test_discord_prompt_only_mode_writes_prompt_file(tmp_path: Path) -> None:
    result = discord_summary_mod.run_discord_summary(
        settings=_settings(),
        window="24h",
        include=None,
        base_dir=tmp_path,
        output=None,
        provider_name=None,
    )
    assert result.mode == "prompt"
    assert result.prompt_path is not None
    assert result.prompt_path.is_file()
    assert "Discord activity" in result.prompt_path.read_text(encoding="utf-8")


def test_discord_run_mode_invokes_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _Provider:
        def summarize(self, prompt: str) -> str:
            return "DISCORD SUMMARY"

    monkeypatch.setattr(
        discord_summary_mod, "get_provider", lambda name, model: _Provider()
    )

    result = discord_summary_mod.run_discord_summary(
        settings=_settings(),
        window="24h",
        include="guild_text",
        base_dir=tmp_path,
        output=None,
        provider_name="opencode",
    )
    assert result.mode == "run"
    assert result.output.read_text(encoding="utf-8") == "DISCORD SUMMARY"


def test_missing_discord_token_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        discord_summary_mod.run_discord_summary(
            settings=_settings(discord_bot_token=None),
            window="24h",
            include=None,
            base_dir=tmp_path,
            output=None,
            provider_name=None,
        )


def test_unknown_include_raises_validation(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        discord_summary_mod.run_discord_summary(
            settings=_settings(),
            window="24h",
            include="guild_text,invalid",
            base_dir=tmp_path,
            output=None,
            provider_name=None,
        )
