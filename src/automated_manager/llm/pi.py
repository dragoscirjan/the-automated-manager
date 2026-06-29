"""Pi.dev agent-CLI provider."""

from __future__ import annotations

from .base import AgentProvider


class PiProvider(AgentProvider):
    """Summarize via ``pi -p`` (print / non-interactive mode)."""

    name = "pi"

    def _command(self, prompt: str) -> list[str]:
        command = ["pi", "-p"]
        if self._model:
            command += ["--model", self._model]
        command.append(prompt)
        return command
