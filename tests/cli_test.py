"""Tests for :mod:`automated_manager.cli`."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from automated_manager import cli as cli_mod
from automated_manager import __version__
from automated_manager.discord.render import ExportResult as DiscordExportResult
from automated_manager.discord_summary import DiscordSummaryResult
from automated_manager.errors import ConfigError, ValidationError
from automated_manager.slack.render import ExportResult
from automated_manager.summarize import SummaryResult

runner = CliRunner()


def _result(mode: str, tmp_path: Path) -> SummaryResult:
    export = ExportResult(folder=tmp_path / "slack" / "2026-06-29", files=())
    return SummaryResult(
        mode=mode,
        export=export,
        output=tmp_path / "summaries" / "slack-2026-06-29.md",
        conversation_count=2,
        prompt_path=(tmp_path / "summaries" / ".slack-2026-06-29.prompt.md")
        if mode == "prompt"
        else None,
    )


def _discord_result(mode: str, tmp_path: Path) -> DiscordSummaryResult:
    export = DiscordExportResult(folder=tmp_path / "discord" / "2026-06-29", files=())
    return DiscordSummaryResult(
        mode=mode,
        export=export,
        output=tmp_path / "summaries" / "discord-2026-06-29.md",
        conversation_count=2,
        prompt_path=(tmp_path / "summaries" / ".discord-2026-06-29.prompt.md")
        if mode == "prompt"
        else None,
    )


def test_version_flag() -> None:
    result = runner.invoke(cli_mod.app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_slack_summary_prompt_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli_mod, "load_settings", lambda: object())
    monkeypatch.setattr(
        cli_mod, "run_summary", lambda **kwargs: _result("prompt", tmp_path)
    )
    result = runner.invoke(cli_mod.app, ["slack-summary"])
    assert result.exit_code == 0
    assert "Prompt written to" in result.stdout
    assert "Collected 2 conversation(s)" in result.stdout


def test_slack_summary_run_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli_mod, "load_settings", lambda: object())
    monkeypatch.setattr(
        cli_mod, "run_summary", lambda **kwargs: _result("run", tmp_path)
    )
    result = runner.invoke(cli_mod.app, ["slack-summary", "-p", "opencode"])
    assert result.exit_code == 0
    assert "Summary written to" in result.stdout


def test_validation_error_exits_2(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom() -> object:
        raise ValidationError("bad window")

    monkeypatch.setattr(cli_mod, "load_settings", _boom)
    result = runner.invoke(cli_mod.app, ["slack-summary"])
    assert result.exit_code == 2
    assert "bad window" in result.stderr


def test_config_error_exits_1(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom() -> object:
        raise ConfigError("no token")

    monkeypatch.setattr(cli_mod, "load_settings", _boom)
    result = runner.invoke(cli_mod.app, ["slack-summary"])
    assert result.exit_code == 1
    assert "no token" in result.stderr


def test_discord_summary_prompt_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli_mod, "load_settings", lambda: object())
    monkeypatch.setattr(
        cli_mod,
        "run_discord_summary",
        lambda **kwargs: _discord_result("prompt", tmp_path),
    )
    result = runner.invoke(cli_mod.app, ["discord-summary"])
    assert result.exit_code == 0
    assert "Prompt written to" in result.stdout


def test_discord_summary_run_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli_mod, "load_settings", lambda: object())
    monkeypatch.setattr(
        cli_mod,
        "run_discord_summary",
        lambda **kwargs: _discord_result("run", tmp_path),
    )
    result = runner.invoke(
        cli_mod.app,
        ["discord-summary", "-p", "opencode", "--include", "guild_text,dm"],
    )
    assert result.exit_code == 0
    assert "Summary written to" in result.stdout
