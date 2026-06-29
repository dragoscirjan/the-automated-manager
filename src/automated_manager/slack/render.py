"""Render collected Slack conversations to Markdown files on disk.

Each conversation becomes one Markdown file under
``<base_dir>/slack/<period-label>/`` so the export is easy to inspect and to
feed into an LLM agent CLI.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, tzinfo
from pathlib import Path

from ..timeparse import Period
from .collector import Conversation, SlackMessage

_SLUG_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class ExportResult:
    """Outcome of an export: the folder and the files written into it."""

    folder: Path
    files: tuple[Path, ...]


def _slugify(title: str) -> str:
    """Turn a conversation title into a filesystem-safe slug."""
    slug = _SLUG_RE.sub("-", title.lower()).strip("-")
    return slug or "conversation"


def _format_time(ts: str, tz: tzinfo) -> str:
    """Format a Slack epoch timestamp as ``YYYY-MM-DD HH:MM`` in ``tz``."""
    try:
        moment = datetime.fromtimestamp(float(ts), tz=tz)
    except (ValueError, OverflowError):
        return ts
    return moment.strftime("%Y-%m-%d %H:%M")


def _render_message(message: SlackMessage, tz: tzinfo, indent: str = "") -> list[str]:
    """Render a message (and its replies) as Markdown bullet lines."""
    lines = [
        f"{indent}- **{message.author}** ({_format_time(message.ts, tz)}): "
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
    folder = base_dir / "slack" / period.label
    folder.mkdir(parents=True, exist_ok=True)

    files: list[Path] = []
    seen: dict[str, int] = {}
    for conversation in conversations:
        slug = _slugify(conversation.title)
        count = seen.get(slug, 0)
        seen[slug] = count + 1
        filename = f"{slug}.md" if count == 0 else f"{slug}-{count + 1}.md"

        path = folder / filename
        path.write_text(conversation_to_markdown(conversation, tz), encoding="utf-8")
        files.append(path)

    return ExportResult(folder=folder, files=tuple(files))
