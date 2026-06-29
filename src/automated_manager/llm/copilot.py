"""GitHub Copilot CLI agent provider."""

from __future__ import annotations

from .base import AgentProvider


class CopilotProvider(AgentProvider):
    """Summarize via ``copilot -p`` (programmatic / non-interactive mode)."""

    name = "copilot"

    def _command(self, prompt: str) -> list[str]:
        command = ["copilot", "-p", prompt]
        if self._model:
            command += ["--model", self._model]
        return command
