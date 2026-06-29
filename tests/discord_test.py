"""Tests for Discord collector and renderer layers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from automated_manager.discord.collector import DiscordCollector
from automated_manager.discord.client import RawConversation, RawMessage
from automated_manager.discord.render import conversation_to_markdown, write_export
from automated_manager.timeparse import Period

_TZ = timezone.utc


def _period() -> Period:
    end = datetime(2026, 6, 29, 12, 0, tzinfo=_TZ)
    return Period(start=end - timedelta(hours=24), end=end)


def test_discord_collector_normalizes_and_skips_empty() -> None:
    raw = [
        RawConversation(
            id="1",
            title="#eng",
            kind="guild_text",
            messages=(RawMessage(ts="100.0", author="alice", text="status update"),),
        ),
        RawConversation(
            id="2",
            title="@bob",
            kind="dm",
            messages=(RawMessage(ts="101.0", author="bob", text="   "),),
        ),
    ]

    conversations = DiscordCollector().normalize(raw)
    assert len(conversations) == 1
    assert conversations[0].title == "#eng"
    assert conversations[0].messages[0].text == "status update"


def test_discord_write_export_writes_files(tmp_path: Path) -> None:
    conversations = DiscordCollector().normalize(
        [
            RawConversation(
                id="1",
                title="#eng",
                kind="guild_text",
                messages=(RawMessage(ts="100.0", author="alice", text="hello"),),
            )
        ]
    )

    result = write_export(conversations, _period(), _TZ, tmp_path)
    assert result.folder == tmp_path / "discord" / "2026-06-28-2026-06-29"
    assert len(result.files) == 1
    assert result.files[0].read_text(encoding="utf-8").startswith("# #eng")


def test_discord_markdown_includes_author_and_text() -> None:
    conversation = DiscordCollector().normalize(
        [
            RawConversation(
                id="1",
                title="#eng",
                kind="guild_text",
                messages=(RawMessage(ts="100.0", author="alice", text="hello"),),
            )
        ]
    )[0]

    markdown = conversation_to_markdown(conversation, _TZ)
    assert "**alice**" in markdown
    assert "hello" in markdown
