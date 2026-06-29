"""Exception hierarchy for The Automated Manager.

Exit-code mapping (see ``cli.py``):
    * :class:`ValidationError`  -> exit 2 (bad user input / arguments)
    * every other error         -> exit 1 (runtime failure)
"""

from __future__ import annotations


class AutomatedManagerError(Exception):
    """Base class for all application errors."""


class ValidationError(AutomatedManagerError):
    """Raised when user-supplied input fails validation (exit code 2)."""


class ConfigError(AutomatedManagerError):
    """Raised when configuration (env / .env) is missing or invalid."""


class SlackCollectionError(AutomatedManagerError):
    """Raised when collecting data from the Slack API fails."""


class DiscordCollectionError(AutomatedManagerError):
    """Raised when collecting data from the Discord API fails."""


class ProviderError(AutomatedManagerError):
    """Raised when an LLM agent-CLI provider fails to produce a summary."""
