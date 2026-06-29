"""OpenCode agent-CLI provider."""

from __future__ import annotations

from .base import AgentProvider


class OpencodeProvider(AgentProvider):
    """Summarize via ``opencode run`` in non-interactive mode."""

    name = "opencode"

    def _command(self, prompt: str) -> list[str]:
        command = ["opencode", "run"]
        if self._model:
            command += ["--model", self._model]
        command.append(prompt)
        return command
