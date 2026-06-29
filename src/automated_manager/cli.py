"""Typer command-line interface for The Automated Manager."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from . import __version__
from .config import load_settings
from .errors import AutomatedManagerError, ValidationError
from .summarize import SummaryResult, run_summary

app = typer.Typer(
    name="am",
    help="The Automated Manager - tooling for team leads.",
    no_args_is_help=True,
    add_completion=False,
)


def _report(result: SummaryResult) -> None:
    """Print a human-readable summary of the run."""
    typer.echo(
        f"Collected {result.conversation_count} conversation(s); "
        f"exported to {result.export.folder}"
    )
    if result.mode == "run":
        typer.echo(f"Summary written to {result.output}")
    else:
        typer.echo(f"Prompt written to {result.prompt_path}")
        typer.echo(
            "Prompt-only mode: paste it into an agent harness, or re-run with "
            "--provider to generate the summary automatically."
        )


@app.command("slack-summary")
def slack_summary(
    since: Annotated[
        str,
        typer.Option("--since", "-s", help="Time window: Nh or Nd (max 10d)."),
    ] = "24h",
    provider: Annotated[
        str | None,
        typer.Option(
            "--provider",
            "-p",
            help="Agent CLI to run (opencode/claude/pi/copilot). "
            "Omit for prompt-only mode.",
        ),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Summary output file path."),
    ] = None,
) -> None:
    """Summarize Slack activity visible to you over a time window."""
    try:
        settings = load_settings()
        result = run_summary(
            settings=settings,
            window=since,
            base_dir=Path.cwd(),
            output=output,
            provider_name=provider,
        )
        _report(result)
    except ValidationError as err:
        typer.echo(f"Error: {err}", err=True)
        raise typer.Exit(code=2) from err
    except AutomatedManagerError as err:
        typer.echo(f"Error: {err}", err=True)
        raise typer.Exit(code=1) from err


def _version_callback(value: bool) -> None:  # pragma: no cover - trivial
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    _version: Annotated[
        bool,
        typer.Option(
            "--version", callback=_version_callback, is_eager=True, help="Show version."
        ),
    ] = False,
) -> None:
    """The Automated Manager CLI."""
