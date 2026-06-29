"""Collect Slack conversations into immutable domain objects.

The collector walks every conversation visible to the user, fetches messages
(and thread replies) within the requested :class:`~automated_manager.timeparse.Period`,
resolves user IDs / mentions to human names, and skips empty conversations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..timeparse import Period
from .client import SlackClient

#: Message subtypes that carry no conversational value.
_SKIP_SUBTYPES = frozenset(
    {
        "channel_join",
        "channel_leave",
        "channel_topic",
        "channel_purpose",
        "channel_name",
        "group_join",
        "group_leave",
    }
)

_MENTION_RE = re.compile(r"<@(?P<id>[UW][A-Z0-9]+)>")


@dataclass(frozen=True)
class SlackMessage:
    """A single Slack message and any thread replies beneath it."""

    ts: str
    author: str
    text: str
    replies: tuple[SlackMessage, ...] = ()


@dataclass(frozen=True)
class Conversation:
    """A Slack conversation and its in-window messages."""

    id: str
    title: str
    kind: str
    messages: tuple[SlackMessage, ...] = field(default=())


class SlackCollector:
    """Collect in-window Slack conversations into domain objects."""

    def __init__(self, client: SlackClient) -> None:
        self._client = client
        self._user_names: dict[str, str] = {}

    def collect(self, period: Period) -> list[Conversation]:
        """Collect all non-empty conversations within ``period``.

        Args:
            period: The resolved summary window.

        Returns:
            A list of :class:`Conversation`, omitting any with no messages.
        """
        self._user_names = self._build_user_map()
        conversations: list[Conversation] = []
        for raw in self._client.conversations():
            conversation = self._collect_conversation(raw, period)
            if conversation.messages:
                conversations.append(conversation)
        return conversations

    def _build_user_map(self) -> dict[str, str]:
        """Map user IDs to the best available display name."""
        names: dict[str, str] = {}
        for member in self._client.users():
            user_id = member.get("id")
            if not user_id:
                continue
            profile = member.get("profile") or {}
            names[user_id] = (
                profile.get("display_name")
                or profile.get("real_name")
                or member.get("real_name")
                or member.get("name")
                or user_id
            )
        return names

    def _collect_conversation(
        self, raw: dict[str, Any], period: Period
    ) -> Conversation:
        """Build a single :class:`Conversation` from a raw channel record."""
        channel_id = raw["id"]
        title, kind = self._describe(raw)
        messages: list[SlackMessage] = []
        for raw_message in self._client.history(
            channel_id, period.oldest_ts, period.latest_ts
        ):
            message = self._build_message(channel_id, raw_message, period)
            if message is not None:
                messages.append(message)
        messages.sort(key=lambda message: float(message.ts))
        return Conversation(
            id=channel_id, title=title, kind=kind, messages=tuple(messages)
        )

    def _build_message(
        self, channel_id: str, raw: dict[str, Any], period: Period
    ) -> SlackMessage | None:
        """Convert a raw message dict into a :class:`SlackMessage`."""
        if raw.get("subtype") in _SKIP_SUBTYPES:
            return None
        text = (raw.get("text") or "").strip()
        ts = raw.get("ts", "")
        if not text or not ts:
            return None

        replies = self._collect_replies(channel_id, raw, period)
        return SlackMessage(
            ts=ts,
            author=self._author(raw),
            text=self._resolve_mentions(text),
            replies=replies,
        )

    def _collect_replies(
        self, channel_id: str, raw: dict[str, Any], period: Period
    ) -> tuple[SlackMessage, ...]:
        """Fetch thread replies for a parent message, if any."""
        is_thread_parent = (
            raw.get("thread_ts") == raw.get("ts") and raw.get("reply_count", 0) > 0
        )
        if not is_thread_parent:
            return ()

        replies: list[SlackMessage] = []
        for raw_reply in self._client.replies(
            channel_id, raw["ts"], period.oldest_ts, period.latest_ts
        ):
            if raw_reply.get("ts") == raw.get("ts"):
                continue  # the parent is echoed first; skip it
            if raw_reply.get("subtype") in _SKIP_SUBTYPES:
                continue
            text = (raw_reply.get("text") or "").strip()
            if not text:
                continue
            replies.append(
                SlackMessage(
                    ts=raw_reply.get("ts", ""),
                    author=self._author(raw_reply),
                    text=self._resolve_mentions(text),
                )
            )
        return tuple(replies)

    def _describe(self, raw: dict[str, Any]) -> tuple[str, str]:
        """Derive a human title and kind for a conversation."""
        if raw.get("is_im"):
            return f"@{self._name(raw.get('user', ''))}", "im"
        if raw.get("is_mpim"):
            return raw.get("name") or "group-dm", "mpim"
        if raw.get("is_private"):
            return f"#{raw.get('name', raw['id'])}", "private_channel"
        return f"#{raw.get('name', raw['id'])}", "public_channel"

    def _author(self, raw: dict[str, Any]) -> str:
        """Resolve a message author's display name."""
        user_id = raw.get("user")
        if user_id:
            return self._name(user_id)
        return raw.get("username") or raw.get("bot_id") or "unknown"

    def _name(self, user_id: str) -> str:
        """Look up a display name, falling back to the raw ID."""
        return self._user_names.get(user_id, user_id)

    def _resolve_mentions(self, text: str) -> str:
        """Replace ``<@U123>`` mentions with ``@display-name``."""
        return _MENTION_RE.sub(lambda match: f"@{self._name(match.group('id'))}", text)
