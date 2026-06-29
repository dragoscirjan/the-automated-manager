"""Tests for :mod:`automated_manager.summarize`."""

from __future__ import annotations

from datetime import timezone
from pathlib import Path

import pytest

from automated_manager import summarize as summarize_mod
from automated_manager.config import Settings
from automated_manager.errors import ConfigError
from automated_manager.slack.collector import Conversation, SlackMessage


def _settings(**overrides: object) -> Settings:
    data: dict[str, object] = {
        "slack_user_token": "xoxp-test",
        "discord_bot_token": "discord-test",
    }
    data.update(overrides)
    return Settings(_env_file=None, **data)  # type: ignore[call-arg]


def _conversations() -> list[Conversation]:
    return [
        Conversation(
            id="C1",
            title="#general",
            kind="public_channel",
            messages=(SlackMessage(ts="1700000000.0", author="alice", text="hi"),),
        )
    ]


@pytest.fixture(autouse=True)
def _patch_collection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(summarize_mod, "SlackClient", lambda token: object())

    class _Collector:
        def __init__(self, client: object) -> None:
            self._client = client

        def collect(self, period: object) -> list[Conversation]:
            return _conversations()

    monkeypatch.setattr(summarize_mod, "SlackCollector", _Collector)
    monkeypatch.setattr(summarize_mod, "resolve_timezone", lambda name: timezone.utc)


def test_prompt_only_mode_writes_prompt_file(tmp_path: Path) -> None:
    result = summarize_mod.run_summary(
        settings=_settings(),
        window="24h",
        base_dir=tmp_path,
        output=None,
        provider_name=None,
    )
    assert result.mode == "prompt"
    assert result.conversation_count == 1
    assert result.prompt_path is not None
    assert result.prompt_path.is_file()
    assert "#general" in result.prompt_path.read_text(encoding="utf-8")
    assert result.export.folder.is_dir()


def test_run_mode_invokes_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _Provider:
        def summarize(self, prompt: str) -> str:
            return "FINAL SUMMARY"

    monkeypatch.setattr(summarize_mod, "get_provider", lambda name, model: _Provider())

    result = summarize_mod.run_summary(
        settings=_settings(),
        window="24h",
        base_dir=tmp_path,
        output=None,
        provider_name="opencode",
    )
    assert result.mode == "run"
    assert result.output.read_text(encoding="utf-8") == "FINAL SUMMARY"


def test_provider_falls_back_to_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    class _Provider:
        def summarize(self, prompt: str) -> str:
            return "S"

    def _fake_get_provider(name: str, model: str | None) -> _Provider:
        captured["name"] = name
        captured["model"] = model
        return _Provider()

    monkeypatch.setattr(summarize_mod, "get_provider", _fake_get_provider)

    summarize_mod.run_summary(
        settings=_settings(llm_provider="claude", llm_model="sonnet"),
        window="24h",
        base_dir=tmp_path,
        output=None,
        provider_name=None,
    )
    assert captured == {"name": "claude", "model": "sonnet"}


def test_missing_slack_token_raises_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError) as raised:
        summarize_mod.run_summary(
            settings=_settings(slack_user_token=None),
            window="24h",
            base_dir=tmp_path,
            output=None,
            provider_name=None,
        )
    assert "SLACK_USER_TOKEN" in str(raised.value)
