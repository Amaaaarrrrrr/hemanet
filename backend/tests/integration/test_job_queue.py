"""Job queue semantics (ADR-003): claim, retry/backoff, DEAD, locks, dedupe."""

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.clock import FrozenClock
from app.extensions import db
from app.jobs.models import Job, JobStatus
from app.jobs.queue import claim_next, describe_error, enqueue, mark_failed, mark_succeeded

LOCK = timedelta(minutes=5)


def job(job_id: int) -> Job:
    db.session.expire_all()
    found = db.session.get(Job, job_id)
    assert found is not None
    return found


@pytest.mark.usefixtures("app")
def test_enqueue_rejects_unknown_job_types(clock: FrozenClock) -> None:
    with pytest.raises(ValueError, match="no handler"):
        enqueue(db.session, "nope", now=clock.now())


@pytest.mark.usefixtures("app")
def test_claim_marks_running_and_locks(clock: FrozenClock) -> None:
    job_id = enqueue(db.session, "test.record", {"a": 1}, now=clock.now())
    assert job_id is not None

    claimed = claim_next(db.session, "w1", now=clock.now(), lock_for=LOCK)

    assert claimed is not None and claimed.id == job_id
    assert claimed.payload == {"a": 1} and claimed.attempt == 1
    row = job(job_id)
    assert row.status == JobStatus.RUNNING
    assert row.locked_by == "w1" and row.locked_until == clock.now() + LOCK
    assert claim_next(db.session, "w2", now=clock.now(), lock_for=LOCK) is None


@pytest.mark.usefixtures("app")
def test_future_jobs_wait_for_run_at(clock: FrozenClock) -> None:
    enqueue(db.session, "test.record", now=clock.now(), run_at=clock.now() + timedelta(minutes=1))

    assert claim_next(db.session, "w1", now=clock.now(), lock_for=LOCK) is None
    clock.advance(timedelta(minutes=1))
    assert claim_next(db.session, "w1", now=clock.now(), lock_for=LOCK) is not None


@pytest.mark.usefixtures("app")
def test_jobs_are_claimed_in_run_at_order(clock: FrozenClock) -> None:
    later = enqueue(db.session, "test.record", now=clock.now())
    earlier = enqueue(
        db.session, "test.record", now=clock.now(), run_at=clock.now() - timedelta(minutes=1)
    )

    first = claim_next(db.session, "w1", now=clock.now(), lock_for=LOCK)
    second = claim_next(db.session, "w1", now=clock.now(), lock_for=LOCK)

    assert first is not None and second is not None
    assert (first.id, second.id) == (earlier, later)


@pytest.mark.usefixtures("app")
def test_dedupe_key_prevents_duplicates(clock: FrozenClock) -> None:
    first = enqueue(db.session, "test.record", now=clock.now(), dedupe_key="once")
    second = enqueue(db.session, "test.record", now=clock.now(), dedupe_key="once")

    assert first is not None and second is None
    assert len(db.session.scalars(select(Job)).all()) == 1


@pytest.mark.usefixtures("app")
def test_success(clock: FrozenClock) -> None:
    job_id = enqueue(db.session, "test.record", now=clock.now())
    assert job_id is not None
    claim_next(db.session, "w1", now=clock.now(), lock_for=LOCK)

    assert mark_succeeded(db.session, job_id, "w1", now=clock.now())
    row = job(job_id)
    assert row.status == JobStatus.SUCCEEDED and row.locked_by is None


@pytest.mark.usefixtures("app")
def test_failures_back_off_then_go_dead(clock: FrozenClock) -> None:
    job_id = enqueue(db.session, "test.record", now=clock.now(), max_attempts=3)
    assert job_id is not None

    for attempt, delay in ((1, 30), (2, 60)):
        claimed = claim_next(db.session, "w1", now=clock.now(), lock_for=LOCK)
        assert claimed is not None and claimed.attempt == attempt
        status = mark_failed(db.session, job_id, "w1", now=clock.now(), error=RuntimeError("x"))
        db.session.commit()  # the caller owns the transaction
        assert status == JobStatus.FAILED
        assert job(job_id).run_at == clock.now() + timedelta(seconds=delay)
        assert claim_next(db.session, "w1", now=clock.now(), lock_for=LOCK) is None
        clock.advance(timedelta(seconds=delay))

    claim_next(db.session, "w1", now=clock.now(), lock_for=LOCK)
    status = mark_failed(db.session, job_id, "w1", now=clock.now(), error=RuntimeError("x"))
    db.session.commit()

    assert status == JobStatus.DEAD
    assert job(job_id).last_error == "RuntimeError: x"
    clock.advance(timedelta(days=1))
    assert claim_next(db.session, "w1", now=clock.now(), lock_for=LOCK) is None


@pytest.mark.usefixtures("app")
def test_permanent_failure_goes_dead_immediately(clock: FrozenClock) -> None:
    job_id = enqueue(db.session, "test.record", now=clock.now())
    assert job_id is not None
    claim_next(db.session, "w1", now=clock.now(), lock_for=LOCK)

    status = mark_failed(
        db.session, job_id, "w1", now=clock.now(), error=ValueError("bad"), permanent=True
    )

    assert status == JobStatus.DEAD


@pytest.mark.usefixtures("app")
def test_expired_lock_is_reclaimed_and_old_owner_loses_it(clock: FrozenClock) -> None:
    job_id = enqueue(db.session, "test.record", now=clock.now())
    assert job_id is not None
    claim_next(db.session, "crashed", now=clock.now(), lock_for=LOCK)
    clock.advance(LOCK + timedelta(seconds=1))

    reclaimed = claim_next(db.session, "w2", now=clock.now(), lock_for=LOCK)

    assert reclaimed is not None and reclaimed.id == job_id and reclaimed.attempt == 2
    assert not mark_succeeded(db.session, job_id, "crashed", now=clock.now())
    assert mark_failed(db.session, job_id, "crashed", now=clock.now(), error=OSError()) is None
    assert job(job_id).locked_by == "w2"


@pytest.mark.usefixtures("app")
def test_expired_lock_on_final_attempt_goes_dead(clock: FrozenClock) -> None:
    job_id = enqueue(db.session, "test.record", now=clock.now(), max_attempts=1)
    assert job_id is not None
    claim_next(db.session, "crashed", now=clock.now(), lock_for=LOCK)
    clock.advance(LOCK + timedelta(seconds=1))

    assert claim_next(db.session, "w2", now=clock.now(), lock_for=LOCK) is None
    assert job(job_id).status == JobStatus.DEAD


def test_stored_errors_are_redacted_and_truncated() -> None:
    text = describe_error(RuntimeError("donor jane@example.com " + "x" * 5000))

    assert text.startswith("RuntimeError: donor [REDACTED]")
    assert len(text) == 1000
