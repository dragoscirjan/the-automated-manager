"""Render collected Discord conversations to Markdown files on disk."""

from __future__ import annotations

from datetime import tzinfo
from pathlib import Path

from ..render_common import ExportResult, format_time, write_conversation_exports
from ..timeparse import Period
from .collector import Conversation, DiscordMessage


def _render_message(message: DiscordMessage, tz: tzinfo) -> str:
    """Render one Discord message as a Markdown bullet line."""
    return f"- **{message.author}** ({format_time(message.ts, tz)}): {message.text}"


def conversation_to_markdown(conversation: Conversation, tz: tzinfo) -> str:
    """Render a full Discord conversation to a Markdown document."""
    header = f"# {conversation.title}\n\n_Type: {conversation.kind}_\n"
    body = "\n".join(_render_message(message, tz) for message in conversation.messages)
    return f"{header}\n{body}\n"


def conversations_to_markdown(conversations: list[Conversation], tz: tzinfo) -> str:
    """Render all Discord conversations into one Markdown blob."""
    return "\n\n---\n\n".join(
        conversation_to_markdown(conversation, tz) for conversation in conversations
    )


def write_export(
    conversations: list[Conversation],
    period: Period,
    tz: tzinfo,
    base_dir: Path,
) -> ExportResult:
    """Write each conversation to ``<base_dir>/discord/<period>/``."""
    return write_conversation_exports(
        conversations=conversations,
        period=period,
        tz=tz,
        base_dir=base_dir,
        prefix="discord",
        title_of=lambda conversation: conversation.title,
        markdown_of=conversation_to_markdown,
    )
