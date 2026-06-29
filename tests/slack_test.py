"""Tests for the Slack collector and renderer using a fake client."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from automated_manager.slack.collector import SlackCollector
from automated_manager.slack.render import conversation_to_markdown, write_export
from automated_manager.timeparse import Period

_TZ = timezone.utc


class FakeSlackClient:
    """In-memory stand-in for :class:`SlackClient`."""

    def __init__(
        self,
        users: list[dict[str, Any]],
        conversations: list[dict[str, Any]],
        history: dict[str, list[dict[str, Any]]],
        replies: dict[tuple[str, str], list[dict[str, Any]]],
    ) -> None:
        self._users = users
        self._conversations = conversations
        self._history = history
        self._replies = replies

    def users(self) -> Iterator[dict[str, Any]]:
        yield from self._users

    def conversations(self) -> Iterator[dict[str, Any]]:
        yield from self._conversations

    def history(
        self, channel_id: str, oldest: str, latest: str
    ) -> Iterator[dict[str, Any]]:
        yield from self._history.get(channel_id, [])

    def replies(
        self, channel_id: str, thread_ts: str, oldest: str, latest: str
    ) -> Iterator[dict[str, Any]]:
        yield from self._replies.get((channel_id, thread_ts), [])


def _build_client() -> FakeSlackClient:
    users = [
        {"id": "U1", "profile": {"display_name": "alice"}},
        {"id": "U2", "profile": {"real_name": "Bob Builder"}},
    ]
    conversations = [
        {"id": "C1", "name": "general", "is_private": False},
        {"id": "C2", "name": "random", "is_private": False},
        {"id": "D1", "is_im": True, "user": "U2"},
    ]
    history = {
        "C1": [
            {
                "ts": "100.0",
                "user": "U1",
                "text": "Hello <@U2>",
                "thread_ts": "100.0",
                "reply_count": 1,
            },
            {"ts": "101.0", "user": "U2", "text": "joined", "subtype": "channel_join"},
        ],
        "C2": [],
        "D1": [{"ts": "200.0", "user": "U2", "text": "DM here"}],
    }
    replies = {
        ("C1", "100.0"): [
            {"ts": "100.0", "user": "U1", "text": "Hello <@U2>"},
            {"ts": "100.5", "user": "U2", "text": "reply text"},
        ]
    }
    return FakeSlackClient(users, conversations, history, replies)


def _period() -> Period:
    end = datetime(2026, 6, 29, 12, 0, tzinfo=_TZ)
    return Period(start=end - timedelta(hours=24), end=end)


def test_collect_skips_empty_and_resolves_names() -> None:
    collector = SlackCollector(_build_client())
    conversations = collector.collect(_period())

    titles = {conv.title for conv in conversations}
    assert titles == {"#general", "@Bob Builder"}  # C2 (empty) skipped

    general = next(c for c in conversations if c.title == "#general")
    assert general.kind == "public_channel"
    assert len(general.messages) == 1

    message = general.messages[0]
    assert message.author == "alice"
    assert message.text == "Hello @Bob Builder"  # mention resolved
    assert len(message.replies) == 1
    assert message.replies[0].author == "Bob Builder"
    assert message.replies[0].text == "reply text"


def test_im_kind_detected() -> None:
    collector = SlackCollector(_build_client())
    conversations = collector.collect(_period())
    dm = next(c for c in conversations if c.title == "@Bob Builder")
    assert dm.kind == "im"
    assert dm.messages[0].text == "DM here"


def test_write_export_creates_one_file_per_conversation(tmp_path: Path) -> None:
    collector = SlackCollector(_build_client())
    conversations = collector.collect(_period())

    result = write_export(conversations, _period(), _TZ, tmp_path)

    assert result.folder == tmp_path / "slack" / "2026-06-28-2026-06-29"
    assert len(result.files) == 2
    for path in result.files:
        assert path.is_file()
        assert path.read_text(encoding="utf-8").startswith("# ")


def test_conversation_to_markdown_includes_replies() -> None:
    collector = SlackCollector(_build_client())
    general = next(c for c in collector.collect(_period()) if c.title == "#general")
    markdown = conversation_to_markdown(general, _TZ)
    assert "**alice**" in markdown
    assert "reply text" in markdown
