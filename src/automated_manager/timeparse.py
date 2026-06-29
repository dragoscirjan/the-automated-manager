"""Parsing and modelling of the summary time window.

The user supplies a window as ``Nh`` (hours) or ``Nd`` (days). The default is
``24h`` and the maximum span is 10 days. A :class:`Period` models the resolved
``[start, end]`` window and derives the canonical folder label:

    * single calendar day -> ``YYYY-MM-DD``
    * multi-day span       -> ``YYYY-MM-DD-YYYY-MM-DD``
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from .errors import ValidationError

_DURATION_RE = re.compile(r"^\s*(?P<value>\d+)\s*(?P<unit>[hd])\s*$")

#: Maximum permitted summary window.
MAX_DURATION = timedelta(days=10)


def parse_duration(spec: str) -> timedelta:
    """Parse a ``Nh`` / ``Nd`` window specification into a :class:`timedelta`.

    Args:
        spec: A window such as ``"24h"`` or ``"7d"``.

    Returns:
        The corresponding positive :class:`timedelta`.

    Raises:
        ValidationError: If the format is invalid, the value is non-positive,
            or the span exceeds :data:`MAX_DURATION`.
    """
    match = _DURATION_RE.match(spec)
    if not match:
        raise ValidationError(
            f"Invalid time window {spec!r}. Use Nh or Nd (e.g. 24h, 7d)."
        )

    value = int(match.group("value"))
    if value <= 0:
        raise ValidationError(f"Time window {spec!r} must be greater than zero.")

    unit = match.group("unit")
    delta = timedelta(hours=value) if unit == "h" else timedelta(days=value)

    if delta > MAX_DURATION:
        raise ValidationError(f"Time window {spec!r} exceeds the maximum of 10 days.")
    return delta


@dataclass(frozen=True)
class Period:
    """A resolved, timezone-aware ``[start, end]`` summary window."""

    start: datetime
    end: datetime

    @property
    def label(self) -> str:
        """Canonical folder label for this period."""
        start_date = self.start.date()
        end_date = self.end.date()
        if start_date == end_date:
            return start_date.isoformat()
        return f"{start_date.isoformat()}-{end_date.isoformat()}"

    @property
    def oldest_ts(self) -> str:
        """Slack ``oldest`` bound as a unix-epoch string."""
        return f"{self.start.timestamp():.6f}"

    @property
    def latest_ts(self) -> str:
        """Slack ``latest`` bound as a unix-epoch string."""
        return f"{self.end.timestamp():.6f}"


def resolve_period(spec: str, now: datetime) -> Period:
    """Resolve a window spec against ``now`` into a :class:`Period`.

    Args:
        spec: A ``Nh`` / ``Nd`` window specification.
        now: The timezone-aware end of the window (typically the current time).

    Returns:
        The resolved :class:`Period` spanning ``[now - delta, now]``.
    """
    delta = parse_duration(spec)
    return Period(start=now - delta, end=now)
