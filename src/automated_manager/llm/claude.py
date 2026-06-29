"""Claude Code agent-CLI provider."""

from __future__ import annotations

from .base import AgentProvider


class ClaudeProvider(AgentProvider):
    """Summarize via ``claude -p`` (print / non-interactive mode)."""

    name = "claude"

    def _command(self, prompt: str) -> list[str]:
        command = ["claude", "-p"]
        if self._model:
            command += ["--model", self._model]
        command.append(prompt)
        return command
