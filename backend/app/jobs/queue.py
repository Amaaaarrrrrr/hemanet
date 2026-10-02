"""PostgreSQL-backed job queue (ADR-003).

* ``enqueue`` writes into the caller's transaction (atomic with the caller's work).
* ``claim_next`` uses ``SELECT … FOR UPDATE SKIP LOCKED`` so concurrent workers
  never claim the same job; the claim is committed immediately.
* A job whose lock expired (worker crashed) is reclaimable.
* Failures retry with exponential backoff (FAILED) until ``max_attempts``, then DEAD.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, or_, select, update
from sqlalchemy.dialects.postgresql import insert

from app.core.db import DbSession
from app.core.logging import redact_text
from app.jobs.models import Job, JobStatus
from app.jobs.registry import get_handler

BACKOFF_BASE = timedelta(seconds=30)
BACKOFF_MAX = timedelta(hours=1)
MAX_ERROR_LENGTH = 1000


@dataclass(frozen=True)
class ClaimedJob:
    id: int
    job_type: str
    payload: dict[str, Any]
    attempt: int
    max_attempts: int


def enqueue(
    session: DbSession,
    job_type: str,
    payload: dict[str, Any] | None = None,
    *,
    now: datetime,
    run_at: datetime | None = None,
    dedupe_key: str | None = None,
    max_attempts: int = 5,
) -> int | None:
    """Queue a job in the current transaction.

    Returns the job id, or ``None`` if a job with the same ``dedupe_key`` exists.
    """
    if get_handler(job_type) is None:
        raise ValueError(f"no handler registered for job type {job_type!r}")
    stmt = (
        insert(Job)
        .values(
            job_type=job_type,
            payload=payload or {},
            run_at=run_at or now,
            status=JobStatus.QUEUED,
            max_attempts=max_attempts,
            dedupe_key=dedupe_key,
            created_at=now,
            updated_at=now,
        )
        .on_conflict_do_nothing(index_elements=[Job.dedupe_key])
        .returning(Job.id)
    )
    job_id: int | None = session.execute(stmt).scalar_one_or_none()
    return job_id


def backoff_delay(attempt: int) -> timedelta:
    """30 s, 60 s, 120 s, … capped at 1 h. ``attempt`` starts at 1."""
    exponent = min(max(attempt - 1, 0), 16)  # cap before multiplying: no overflow
    return min(BACKOFF_BASE * (1 << exponent), BACKOFF_MAX)


def claim_next(
    session: DbSession, worker_id: str, *, now: datetime, lock_for: timedelta
) -> ClaimedJob | None:
    """Claim the next due job and commit the claim. Returns ``None`` if none is due."""
    while True:
        stmt = (
            select(Job)
            .where(
                or_(
                    and_(Job.status.in_([JobStatus.QUEUED, JobStatus.FAILED]), Job.run_at <= now),
                    and_(Job.status == JobStatus.RUNNING, Job.locked_until < now),
                )
            )
            .order_by(Job.run_at, Job.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        job = session.scalars(stmt).first()
        if job is None:
            session.commit()
            return None
        if job.status == JobStatus.RUNNING and job.attempts >= job.max_attempts:
            # The final attempt's worker died: do not run again.
            job.status = JobStatus.DEAD
            job.locked_by = None
            job.locked_until = None
            job.last_error = "lock expired during final attempt"
            job.updated_at = now
            session.commit()
            continue
        job.status = JobStatus.RUNNING
        job.attempts += 1
        job.locked_by = worker_id
        job.locked_until = now + lock_for
        job.updated_at = now
        claimed = ClaimedJob(
            id=job.id,
            job_type=job.job_type,
            payload=dict(job.payload),
            attempt=job.attempts,
            max_attempts=job.max_attempts,
        )
        session.commit()
        return claimed


def mark_succeeded(session: DbSession, job_id: int, worker_id: str, *, now: datetime) -> bool:
    """Mark success in the caller's transaction (commit together with the handler's work)."""
    result = session.execute(
        update(Job)
        .where(Job.id == job_id, Job.locked_by == worker_id, Job.status == JobStatus.RUNNING)
        .values(
            status=JobStatus.SUCCEEDED,
            locked_by=None,
            locked_until=None,
            last_error=None,
            updated_at=now,
        )
    )
    return bool(getattr(result, "rowcount", 0))


def mark_failed(
    session: DbSession,
    job_id: int,
    worker_id: str,
    *,
    now: datetime,
    error: BaseException,
    permanent: bool = False,
) -> JobStatus | None:
    """Record a failed attempt: FAILED with a retry time, or DEAD. Caller commits."""
    job = session.scalars(
        select(Job)
        .where(Job.id == job_id, Job.locked_by == worker_id, Job.status == JobStatus.RUNNING)
        .with_for_update()
    ).first()
    if job is None:
        return None  # lock lost to another worker; it owns the job now
    job.last_error = describe_error(error)
    job.locked_by = None
    job.locked_until = None
    job.updated_at = now
    if permanent or job.attempts >= job.max_attempts:
        job.status = JobStatus.DEAD
    else:
        job.status = JobStatus.FAILED
        job.run_at = now + backoff_delay(job.attempts)
    return job.status


def describe_error(error: BaseException) -> str:
    """Exception type and redacted, truncated message: safe to store and log."""
    text = f"{type(error).__name__}: {redact_text(str(error))}"
    return text[:MAX_ERROR_LENGTH]
