"""Base class for LLM agent-CLI providers.

Each provider shells out to an installed agent CLI in its non-interactive
"print" mode, passing the full prompt as an argument and capturing stdout as
the summary. Because we capture stdout (rather than asking the agent to write
files), no provider needs filesystem-permission flags.
"""

from __future__ import annotations

import subprocess
from abc import ABC, abstractmethod
from typing import ClassVar

from ..errors import ProviderError


class AgentProvider(ABC):
    """Abstract base for agent-CLI summarization providers."""

    name: ClassVar[str]

    def __init__(self, model: str | None = None) -> None:
        self._model = model

    @abstractmethod
    def _command(self, prompt: str) -> list[str]:
        """Build the argv list for invoking the agent CLI with ``prompt``."""

    def summarize(self, prompt: str) -> str:
        """Run the agent CLI and return its stdout as the summary.

        Args:
            prompt: The fully-rendered summarization prompt.

        Returns:
            The trimmed stdout produced by the agent CLI.

        Raises:
            ProviderError: If the CLI is missing, exits non-zero, or returns
                no output.
        """
        command = self._command(prompt)
        try:
            result = subprocess.run(  # noqa: S603 - args are constructed, not shell
                command,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as err:
            raise ProviderError(
                f"Agent CLI {command[0]!r} is not installed or not on PATH."
            ) from err
        except OSError as err:
            raise ProviderError(f"Failed to run {command[0]!r}: {err}") from err

        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            raise ProviderError(
                f"Provider {self.name!r} exited with code {result.returncode}: {stderr}"
            )

        output = (result.stdout or "").strip()
        if not output:
            raise ProviderError(f"Provider {self.name!r} returned empty output.")
        return output
