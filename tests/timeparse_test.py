"""Tests for :mod:`automated_manager.timeparse`."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from automated_manager.errors import ValidationError
from automated_manager.timeparse import (
    MAX_DURATION,
    Period,
    parse_duration,
    resolve_period,
)


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ("24h", timedelta(hours=24)),
        ("1h", timedelta(hours=1)),
        ("7d", timedelta(days=7)),
        ("10d", timedelta(days=10)),
        ("240h", timedelta(hours=240)),
        ("  24h  ", timedelta(hours=24)),
    ],
)
def test_parse_duration_valid(spec: str, expected: timedelta) -> None:
    assert parse_duration(spec) == expected


@pytest.mark.parametrize(
    "spec",
    ["", "5", "5x", "abc", "0h", "0d", "-1h", "11d", "241h", "1.5h", "h", "d"],
)
def test_parse_duration_invalid(spec: str) -> None:
    with pytest.raises(ValidationError):
        parse_duration(spec)


def test_max_duration_is_ten_days() -> None:
    assert MAX_DURATION == timedelta(days=10)
    assert parse_duration("240h") == MAX_DURATION


def test_period_label_single_day() -> None:
    start = datetime(2026, 6, 29, 8, 0, tzinfo=timezone.utc)
    end = datetime(2026, 6, 29, 20, 0, tzinfo=timezone.utc)
    assert Period(start=start, end=end).label == "2026-06-29"


def test_period_label_range() -> None:
    start = datetime(2026, 6, 25, 8, 0, tzinfo=timezone.utc)
    end = datetime(2026, 6, 29, 8, 0, tzinfo=timezone.utc)
    assert Period(start=start, end=end).label == "2026-06-25-2026-06-29"


def test_period_timestamps() -> None:
    start = datetime(2026, 6, 29, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 6, 29, 1, 0, tzinfo=timezone.utc)
    period = Period(start=start, end=end)
    assert period.oldest_ts == f"{start.timestamp():.6f}"
    assert period.latest_ts == f"{end.timestamp():.6f}"


def test_resolve_period_spans_window() -> None:
    now = datetime(2026, 6, 29, 12, 0, tzinfo=timezone.utc)
    period = resolve_period("24h", now)
    assert period.end == now
    assert period.start == now - timedelta(hours=24)
