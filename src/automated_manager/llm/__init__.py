"""LLM agent-CLI providers and prompt construction."""

from __future__ import annotations

from ..errors import ValidationError
from .base import AgentProvider
from .claude import ClaudeProvider
from .copilot import CopilotProvider
from .opencode import OpencodeProvider
from .pi import PiProvider
from .prompt import build_prompt

_PROVIDERS: dict[str, type[AgentProvider]] = {
    provider.name: provider
    for provider in (
        OpencodeProvider,
        ClaudeProvider,
        PiProvider,
        CopilotProvider,
    )
}


def available_providers() -> list[str]:
    """Return the sorted list of registered provider names."""
    return sorted(_PROVIDERS)


def get_provider(name: str, model: str | None = None) -> AgentProvider:
    """Instantiate a provider by name.

    Args:
        name: Registered provider name (``opencode``/``claude``/``pi``/``copilot``).
        model: Optional model identifier passed through to the CLI.

    Returns:
        An :class:`AgentProvider` instance.

    Raises:
        ValidationError: If ``name`` is not a registered provider.
    """
    try:
        provider_cls = _PROVIDERS[name]
    except KeyError as err:
        raise ValidationError(
            f"Unknown provider {name!r}. "
            f"Choose one of: {', '.join(available_providers())}."
        ) from err
    return provider_cls(model)


__all__ = [
    "AgentProvider",
    "available_providers",
    "build_prompt",
    "get_provider",
]
