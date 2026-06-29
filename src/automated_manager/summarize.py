"""Orchestration: collect Slack activity, export it, and summarize it.

Two execution modes:

* **prompt-only** (default): write a self-contained prompt file the user can
  paste into any agent harness. No LLM is invoked.
* **run**: invoke a configured agent CLI provider, capture its stdout, and
  write the finished summary to the output path.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .config import Settings, resolve_timezone
from .errors import ConfigError
from .llm import build_prompt, get_provider
from .slack import SlackClient, SlackCollector, write_export
from .slack.render import ExportResult, conversations_to_markdown
from .timeparse import resolve_period


@dataclass(frozen=True)
class SummaryResult:
    """Outcome of a summary run."""

    mode: str
    export: ExportResult
    output: Path
    conversation_count: int
    prompt_path: Path | None = None


def run_summary(
    settings: Settings,
    window: str,
    base_dir: Path,
    output: Path | None,
    provider_name: str | None,
) -> SummaryResult:
    """Collect Slack activity for ``window`` and produce a summary artifact.

    Args:
        settings: Loaded application settings (token, provider, model, tz).
        window: The ``Nh`` / ``Nd`` window specification.
        base_dir: Root directory for exports and summaries (typically cwd).
        output: Explicit summary output path, or ``None`` for the default.
        provider_name: Agent CLI provider to run, or ``None`` for prompt-only
            mode (falls back to ``settings.llm_provider``).

    Returns:
        A :class:`SummaryResult` describing what was produced.
    """
    if not settings.slack_user_token:
        raise ConfigError(
            "Missing SLACK_USER_TOKEN. Configure it via environment variable "
            "or a .env file in the current directory."
        )

    tz = resolve_timezone(settings.timezone)
    period = resolve_period(window, datetime.now(tz))

    conversations = SlackCollector(SlackClient(settings.slack_user_token)).collect(
        period
    )
    export = write_export(conversations, period, tz, base_dir)

    summaries_dir = base_dir / "summaries"
    output_path = output or summaries_dir / f"slack-{period.label}.md"
    prompt = build_prompt(
        period,
        export.folder,
        output_path,
        conversations_to_markdown(conversations, tz),
    )

    resolved_provider = provider_name or settings.llm_provider
    if resolved_provider:
        return _run_provider(
            resolved_provider, settings.llm_model, prompt, export, output_path
        )
    return _write_prompt(
        prompt, summaries_dir / f".slack-{period.label}.prompt.md", export, output_path
    )


def _run_provider(
    name: str,
    model: str | None,
    prompt: str,
    export: ExportResult,
    output_path: Path,
) -> SummaryResult:
    """Run an agent CLI provider and write its summary to ``output_path``."""
    summary = get_provider(name, model).summarize(prompt)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(summary, encoding="utf-8")
    return SummaryResult(
        mode="run",
        export=export,
        output=output_path,
        conversation_count=len(export.files),
    )


def _write_prompt(
    prompt: str,
    prompt_path: Path,
    export: ExportResult,
    output_path: Path,
) -> SummaryResult:
    """Write a paste-ready prompt file for prompt-only mode."""
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt, encoding="utf-8")
    return SummaryResult(
        mode="prompt",
        export=export,
        output=output_path,
        conversation_count=len(export.files),
        prompt_path=prompt_path,
    )
