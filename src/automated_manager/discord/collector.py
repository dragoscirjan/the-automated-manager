"""Normalize raw Discord payloads into immutable domain objects."""

from __future__ import annotations

from dataclasses import dataclass, field

from .client import RawConversation, RawMessage


@dataclass(frozen=True)
class DiscordMessage:
    """A single Discord message."""

    ts: str
    author: str
    text: str


@dataclass(frozen=True)
class Conversation:
    """A Discord conversation and its in-window messages."""

    id: str
    title: str
    kind: str
    messages: tuple[DiscordMessage, ...] = field(default=())


class DiscordCollector:
    """Convert :class:`RawConversation` payloads into domain objects."""

    def normalize(self, conversations: list[RawConversation]) -> list[Conversation]:
        """Return normalized conversations, skipping empties defensively."""
        normalized: list[Conversation] = []
        for conversation in conversations:
            messages = tuple(
                DiscordMessage(ts=msg.ts, author=msg.author, text=msg.text)
                for msg in conversation.messages
                if msg.text.strip()
            )
            if not messages:
                continue
            normalized.append(
                Conversation(
                    id=conversation.id,
                    title=conversation.title,
                    kind=conversation.kind,
                    messages=messages,
                )
            )
        return normalized


def from_raw_message(raw: RawMessage) -> DiscordMessage:
    """Convert one raw Discord message into a normalized message."""
    return DiscordMessage(ts=raw.ts, author=raw.author, text=raw.text)
