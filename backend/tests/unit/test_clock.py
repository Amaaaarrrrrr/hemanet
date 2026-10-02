from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.core.clock import FrozenClock, SystemClock, get_clock, utcnow


def test_frozen_clock_set_and_advance() -> None:
    clock = FrozenClock(datetime(2026, 1, 1, tzinfo=UTC))
    clock.advance(timedelta(minutes=5))
    assert clock.now() == datetime(2026, 1, 1, 0, 5, tzinfo=UTC)
    clock.set(datetime(2026, 1, 1, 3, tzinfo=timezone(timedelta(hours=3))))
    assert clock.now() == datetime(2026, 1, 1, 0, 0, tzinfo=UTC)  # normalised to UTC


def test_frozen_clock_rejects_naive_datetimes() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        FrozenClock(datetime(2026, 1, 1))


def test_outside_an_app_the_system_clock_is_used() -> None:
    assert isinstance(get_clock(), SystemClock)
    assert utcnow().tzinfo is UTC
