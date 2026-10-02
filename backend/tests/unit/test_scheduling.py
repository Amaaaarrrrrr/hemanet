from datetime import UTC, datetime, timedelta

import pytest

from app.jobs.queue import backoff_delay
from app.jobs.scheduler import slot_start


def test_slots_align_to_fixed_boundaries() -> None:
    now = datetime(2026, 10, 2, 9, 47, 12, tzinfo=UTC)

    assert slot_start(now, timedelta(hours=1)) == datetime(2026, 10, 2, 9, 0, tzinfo=UTC)
    assert slot_start(now, timedelta(minutes=15)) == datetime(2026, 10, 2, 9, 45, tzinfo=UTC)


def test_slot_period_must_be_positive() -> None:
    with pytest.raises(ValueError, match="positive"):
        slot_start(datetime(2026, 1, 1, tzinfo=UTC), timedelta(0))


@pytest.mark.parametrize(
    ("attempt", "seconds"), [(1, 30), (2, 60), (3, 120), (4, 240), (8, 3600), (50, 3600)]
)
def test_exponential_backoff_is_capped_at_one_hour(attempt: int, seconds: int) -> None:
    assert backoff_delay(attempt) == timedelta(seconds=seconds)
