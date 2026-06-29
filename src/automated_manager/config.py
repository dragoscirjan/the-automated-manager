"""Application configuration loaded from environment variables / ``.env``.

Secrets and runtime options are read from environment variables, optionally
seeded by a ``.env`` file discovered by walking up from the current working
directory. This keeps secrets out of the codebase and lets the tool run from
any project folder via ``uvx``.
"""

from __future__ import annotations

from datetime import datetime, tzinfo
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, ValidationError as PydanticValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from .errors import ConfigError


def find_dotenv(start: Path | None = None) -> Path | None:
    """Locate the nearest ``.env`` file by walking up from ``start``.

    Args:
        start: Directory to begin the search from. Defaults to the current
            working directory.

    Returns:
        The path to the closest ``.env`` file, or ``None`` if none is found.
    """
    current = (start or Path.cwd()).resolve()
    for directory in (current, *current.parents):
        candidate = directory / ".env"
        if candidate.is_file():
            return candidate
    return None


class Settings(BaseSettings):
    """Runtime configuration sourced from the environment / ``.env``."""

    slack_user_token: str = Field(validation_alias="SLACK_USER_TOKEN")
    llm_provider: str | None = Field(default=None, validation_alias="LLM_PROVIDER")
    llm_model: str | None = Field(default=None, validation_alias="LLM_MODEL")
    timezone: str | None = Field(default=None, validation_alias="AM_TIMEZONE")

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )


def load_settings(start: Path | None = None) -> Settings:
    """Load and validate :class:`Settings`.

    Args:
        start: Directory to begin the ``.env`` search from.

    Returns:
        The populated :class:`Settings` instance.

    Raises:
        ConfigError: If required settings (e.g. ``SLACK_USER_TOKEN``) are absent.
    """
    env_file = find_dotenv(start)
    try:
        return Settings(_env_file=env_file)  # type: ignore[call-arg]
    except PydanticValidationError as err:
        raise ConfigError(
            "Invalid configuration. Ensure SLACK_USER_TOKEN is set via an "
            "environment variable or a .env file in the current directory.\n"
            f"{err}"
        ) from err


def resolve_timezone(name: str | None) -> tzinfo:
    """Resolve a timezone name into a :class:`tzinfo`.

    Args:
        name: An IANA timezone name (e.g. ``"Europe/Bucharest"``), or ``None``
            to use the system local timezone.

    Returns:
        The resolved :class:`tzinfo`.

    Raises:
        ConfigError: If ``name`` is not a known timezone.
    """
    if not name:
        local = datetime.now().astimezone().tzinfo
        if local is None:  # pragma: no cover - astimezone always sets tzinfo
            raise ConfigError("Unable to determine the local timezone.")
        return local
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as err:
        raise ConfigError(f"Unknown timezone {name!r}.") from err
