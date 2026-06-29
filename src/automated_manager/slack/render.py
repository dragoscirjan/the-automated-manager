"""Render collected Slack conversations to Markdown files on disk.

Each conversation becomes one Markdown file under
``<base_dir>/slack/<period-label>/`` so the export is easy to inspect and to
feed into an LLM agent CLI.
"""

from __future__ import annotations

from datetime import tzinfo
from pathlib import Path

from ..render_common import ExportResult, format_time, write_conversation_exports
from ..timeparse import Period
from .collector import Conversation, SlackMessage


def _render_message(message: SlackMessage, tz: tzinfo, indent: str = "") -> list[str]:
    """Render a message (and its replies) as Markdown bullet lines."""
    lines = [
        f"{indent}- **{message.author}** ({format_time(message.ts, tz)}): "
        f"{message.text}"
    ]
    for reply in message.replies:
        lines.extend(_render_message(reply, tz, indent + "    "))
    return lines


def conversation_to_markdown(conversation: Conversation, tz: tzinfo) -> str:
    """Render a full conversation to a Markdown document."""
    header = f"# {conversation.title}\n\n_Type: {conversation.kind}_\n"
    body: list[str] = []
    for message in conversation.messages:
        body.extend(_render_message(message, tz))
    return f"{header}\n" + "\n".join(body) + "\n"


def conversations_to_markdown(conversations: list[Conversation], tz: tzinfo) -> str:
    """Render every conversation into a single Markdown document.

    Args:
        conversations: The collected conversations to render.
        tz: Timezone used to render message timestamps.

    Returns:
        All conversations joined by a horizontal rule, suitable for inlining
        into a prompt.
    """
    return "\n\n---\n\n".join(
        conversation_to_markdown(conversation, tz) for conversation in conversations
    )


def write_export(
    conversations: list[Conversation],
    period: Period,
    tz: tzinfo,
    base_dir: Path,
) -> ExportResult:
    """Write each conversation to ``<base_dir>/slack/<period>/`` as Markdown.

    Args:
        conversations: The collected conversations to export.
        period: The summary window (its label names the folder).
        tz: Timezone used to render message timestamps.
        base_dir: Root directory (typically the current working directory).

    Returns:
        An :class:`ExportResult` with the folder and written file paths.
    """
    return write_conversation_exports(
        conversations=conversations,
        period=period,
        tz=tz,
        base_dir=base_dir,
        prefix="slack",
        title_of=lambda conversation: conversation.title,
        markdown_of=conversation_to_markdown,
    )
