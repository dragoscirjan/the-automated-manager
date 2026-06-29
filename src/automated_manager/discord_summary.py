"""Orchestration: collect Discord activity, export it, and summarize it."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .config import Settings, resolve_timezone
from .discord import DiscordClient, write_export
from .discord.collector import DiscordCollector
from .discord.render import ExportResult, conversations_to_markdown
from .errors import ConfigError, ValidationError
from .llm import build_prompt, get_provider
from .timeparse import resolve_period

_DEFAULT_INCLUDE = "guild_text,thread,dm,group_dm"
_ALLOWED_INCLUDE = frozenset({"guild_text", "thread", "dm", "group_dm"})


@dataclass(frozen=True)
class DiscordSummaryResult:
    """Outcome of a Discord summary run."""

    mode: str
    export: ExportResult
    output: Path
    conversation_count: int
    prompt_path: Path | None = None


def parse_include(spec: str | None) -> set[str]:
    """Parse ``--include`` value into allowed conversation kinds."""
    raw = (spec or _DEFAULT_INCLUDE).strip()
    values = {item.strip() for item in raw.split(",") if item.strip()}
    if not values:
        values = set(_DEFAULT_INCLUDE.split(","))
    unknown = values - _ALLOWED_INCLUDE
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ValidationError(
            f"Unknown include kinds: {names}. "
            "Allowed: guild_text, thread, dm, group_dm."
        )
    return values


@dataclass(frozen=True)
class _DiscordArtifacts:
    export: ExportResult
    output_path: Path
    prompt: str
    period_label: str


def run_discord_summary(
    settings: Settings,
    *,
    window: str,
    include: str | None,
    base_dir: Path,
    output: Path | None,
    provider_name: str | None,
) -> DiscordSummaryResult:
    """Collect Discord activity for ``window`` and produce summary artifacts."""
    artifacts = _prepare_artifacts(
        settings=settings,
        window=window,
        include=include,
        base_dir=base_dir,
        output=output,
    )
    resolved_provider = provider_name or settings.llm_provider
    if resolved_provider:
        return _run_provider(
            name=resolved_provider,
            model=settings.llm_model,
            prompt=artifacts.prompt,
            export=artifacts.export,
            output_path=artifacts.output_path,
        )

    prompt_path = (
        base_dir / "summaries" / f".discord-{artifacts.period_label}.prompt.md"
    )
    return _write_prompt(
        prompt=artifacts.prompt,
        prompt_path=prompt_path,
        export=artifacts.export,
        output_path=artifacts.output_path,
    )


def _prepare_artifacts(
    settings: Settings,
    window: str,
    include: str | None,
    base_dir: Path,
    output: Path | None,
) -> _DiscordArtifacts:
    """Collect and render Discord data, then build summary prompt content."""
    token = settings.discord_bot_token
    if not token:
        raise ConfigError(
            "Missing DISCORD_BOT_TOKEN. Configure it via environment variable "
            "or a .env file in the current directory."
        )

    tz = resolve_timezone(settings.timezone)
    period = resolve_period(window, datetime.now(tz))
    include_kinds = parse_include(include)

    raw = DiscordClient(token).collect(period, include_kinds)
    conversations = DiscordCollector().normalize(raw)
    export = write_export(conversations, period, tz, base_dir)

    summaries_dir = base_dir / "summaries"
    output_path = output or summaries_dir / f"discord-{period.label}.md"
    prompt = build_prompt(
        period,
        export.folder,
        output_path,
        conversations_to_markdown(conversations, tz),
    ).replace("Slack activity", "Discord activity")

    return _DiscordArtifacts(
        export=export,
        output_path=output_path,
        prompt=prompt,
        period_label=period.label,
    )


def _run_provider(
    *,
    name: str,
    model: str | None,
    prompt: str,
    export: ExportResult,
    output_path: Path,
) -> DiscordSummaryResult:
    summary = get_provider(name, model).summarize(prompt)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(summary, encoding="utf-8")
    return DiscordSummaryResult(
        mode="run",
        export=export,
        output=output_path,
        conversation_count=len(export.files),
    )


def _write_prompt(
    *,
    prompt: str,
    prompt_path: Path,
    export: ExportResult,
    output_path: Path,
) -> DiscordSummaryResult:
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt, encoding="utf-8")
    return DiscordSummaryResult(
        mode="prompt",
        export=export,
        output=output_path,
        conversation_count=len(export.files),
        prompt_path=prompt_path,
    )
