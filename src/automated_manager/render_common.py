"""Shared Markdown export helpers for conversation renderers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, tzinfo
from pathlib import Path
from typing import Callable, TypeVar

from .timeparse import Period

_SLUG_RE = re.compile(r"[^a-z0-9]+")
_Conversation = TypeVar("_Conversation")


@dataclass(frozen=True)
class ExportResult:
    """Outcome of an export: folder and files written under it."""

    folder: Path
    files: tuple[Path, ...]


def slugify(title: str) -> str:
    """Turn a title into a filesystem-safe slug."""
    slug = _SLUG_RE.sub("-", title.lower()).strip("-")
    return slug or "conversation"


def format_time(ts: str, tz: tzinfo) -> str:
    """Format an epoch timestamp as ``YYYY-MM-DD HH:MM`` in ``tz``."""
    try:
        moment = datetime.fromtimestamp(float(ts), tz=tz)
    except (ValueError, OverflowError):
        return ts
    return moment.strftime("%Y-%m-%d %H:%M")


def write_conversation_exports(
    *,
    conversations: list[_Conversation],
    period: Period,
    tz: tzinfo,
    base_dir: Path,
    prefix: str,
    title_of: Callable[[_Conversation], str],
    markdown_of: Callable[[_Conversation, tzinfo], str],
) -> ExportResult:
    """Write one Markdown file per conversation under ``<base>/<prefix>/<period>``."""
    folder = base_dir / prefix / period.label
    folder.mkdir(parents=True, exist_ok=True)

    files: list[Path] = []
    seen: dict[str, int] = {}
    for conversation in conversations:
        slug = slugify(title_of(conversation))
        count = seen.get(slug, 0)
        seen[slug] = count + 1
        filename = f"{slug}.md" if count == 0 else f"{slug}-{count + 1}.md"

        path = folder / filename
        path.write_text(markdown_of(conversation, tz), encoding="utf-8")
        files.append(path)

    return ExportResult(folder=folder, files=tuple(files))
