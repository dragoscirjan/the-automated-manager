"""Construction of the executive-summary prompt.

The prompt is fully self-contained: it carries the instructions *and* the
exported Slack activity inlined as Markdown, so it can either be piped to an
agent CLI (run mode) or saved for manual use in an agent harness (prompt-only
mode). The source folder and intended output path are included for provenance.
"""

from __future__ import annotations

from pathlib import Path

from ..timeparse import Period

_INSTRUCTIONS = """\
You are an executive assistant to a team lead. Summarize the Slack activity \
below for the period {label}.

Source export folder: {folder}
Intended summary file: {output}

Write a concise, well-structured Markdown summary that covers:

1. **Highlights** - the most important things that happened, at a glance.
2. **Per-conversation notes** - key discussions and decisions, grouped by \
channel / DM.
3. **Action items** - concrete tasks and who owns them (use the names that \
appear in the messages).
4. **Needs attention** - anything blocked, urgent, or requiring the team \
lead's input.

Be factual: only use information present in the messages below. If a section \
has nothing to report, say so briefly. Do not invent owners or decisions.

---

# Slack activity ({label})

{conversations}
"""


def build_prompt(
    period: Period,
    export_folder: Path,
    output_path: Path,
    conversations_markdown: str,
) -> str:
    """Render the full summarization prompt with inlined Slack activity.

    Args:
        period: The resolved summary :class:`~automated_manager.timeparse.Period`.
        export_folder: Folder where the per-conversation Markdown was written.
        output_path: Intended destination of the final summary.
        conversations_markdown: Combined Markdown of all conversations.

    Returns:
        The complete, self-contained prompt string.
    """
    body = conversations_markdown.strip() or "_No activity in this period._"
    return _INSTRUCTIONS.format(
        label=period.label,
        folder=export_folder,
        output=output_path,
        conversations=body,
    )
