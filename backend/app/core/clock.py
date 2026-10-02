"""Injectable clock (blueprint §P.1 ``core/clock.py``).

All application time comes from here so tests can freeze or advance time.
Timestamps are always timezone-aware UTC (NFR-T1).
"""

from datetime import UTC, datetime, timedelta
from typing import Protocol

from flask import current_app, has_app_context

CLOCK_EXTENSION_KEY = "hemanet.clock"


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class FrozenClock:
    """A controllable clock for tests."""

    def __init__(self, at: datetime) -> None:
        self._at = _require_aware(at)

    def now(self) -> datetime:
        return self._at

    def set(self, at: datetime) -> None:
        self._at = _require_aware(at)

    def advance(self, delta: timedelta) -> None:
        self._at += delta


def _require_aware(at: datetime) -> datetime:
    if at.tzinfo is None:
        raise ValueError("clock times must be timezone-aware")
    return at.astimezone(UTC)


_system_clock = SystemClock()


def get_clock() -> Clock:
    """The current app's clock, or the system clock outside an app context."""
    if has_app_context():
        clock: Clock | None = current_app.extensions.get(CLOCK_EXTENSION_KEY)
        if clock is not None:
            return clock
    return _system_clock


def utcnow() -> datetime:
    return get_clock().now()
