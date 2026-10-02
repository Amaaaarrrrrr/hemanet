"""Recurring jobs. Every worker runs the scheduler; dedupe keys per time slot
guarantee each slot is enqueued exactly once however many workers run."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.db import DbSession
from app.jobs.queue import enqueue

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


@dataclass(frozen=True)
class Schedule:
    name: str
    job_type: str
    every: timedelta
    payload: dict[str, Any] = field(default_factory=dict)


def slot_start(now: datetime, every: timedelta) -> datetime:
    """Start of the fixed time slot (aligned to the Unix epoch) containing ``now``."""
    period = int(every.total_seconds())
    if period <= 0:
        raise ValueError("schedule period must be positive")
    elapsed = int((now - _EPOCH).total_seconds())
    return _EPOCH + timedelta(seconds=elapsed - elapsed % period)


def enqueue_due(session: DbSession, schedules: Sequence[Schedule], *, now: datetime) -> int:
    """Enqueue the current slot of every schedule (idempotent). Caller commits."""
    created = 0
    for schedule in schedules:
        start = slot_start(now, schedule.every)
        job_id = enqueue(
            session,
            schedule.job_type,
            schedule.payload,
            now=now,
            run_at=start,
            dedupe_key=f"schedule:{schedule.name}:{start.isoformat()}",
        )
        created += job_id is not None
    return created


DEFAULT_SCHEDULES: tuple[Schedule, ...] = (
    Schedule(
        name="purge-expired-idempotency-keys",
        job_type="maintenance.purge_expired_idempotency_keys",
        every=timedelta(hours=1),
    ),
)
