from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from app.domain.exceptions import ValidationError
from app.domain.timeframes import days_until, format_local, local_date, local_day_bounds

CHICAGO = "America/Chicago"


def test_late_evening_chicago_is_still_the_same_local_day() -> None:
    # 04:30 UTC on Oct 6 is 23:30 CDT on Oct 5.
    at = datetime(2026, 10, 6, 4, 30, tzinfo=UTC)
    assert local_date(at, CHICAGO) == date(2026, 10, 5)
    start, end = local_day_bounds(at, CHICAGO)
    assert start == datetime(2026, 10, 5, 5, 0, tzinfo=UTC)
    assert end == datetime(2026, 10, 6, 5, 0, tzinfo=UTC)


def test_bounds_across_dst_end_are_25_hours_long() -> None:
    # DST ends 2026-11-01 in Chicago: that local day has 25 hours.
    at = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
    start, end = local_day_bounds(at, CHICAGO)
    assert (end - start).total_seconds() == 25 * 3600


def test_format_local_carries_offset() -> None:
    assert (
        format_local(datetime(2026, 10, 5, 20, 0, tzinfo=UTC), CHICAGO) == "2026-10-05T15:00-05:00"
    )


def test_days_until_uses_local_date() -> None:
    at = datetime(2026, 10, 6, 4, 30, tzinfo=UTC)  # Oct 5 locally
    assert days_until(date(2026, 10, 10), at, CHICAGO) == 5
    assert days_until(date(2026, 10, 10), at, "UTC") == 4


def test_unknown_timezone_is_a_validation_error() -> None:
    with pytest.raises(ValidationError):
        local_date(datetime.now(UTC), "Mars/Olympus")
