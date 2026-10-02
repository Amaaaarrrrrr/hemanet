"""Transactional outbox → handler jobs."""

import uuid

import pytest
from sqlalchemy import func, select

from app.core.clock import FrozenClock
from app.core.outbox import OutboxEvent, publish_event
from app.extensions import db
from app.jobs.models import Job, JobStatus
from app.jobs.outbox_dispatch import HANDLE_JOB_TYPE, dispatch_pending, event_handler
from app.jobs.worker import Worker

handled: list[uuid.UUID] = []


@event_handler("test.thing_happened", "recorder")
def _record(event: OutboxEvent, _session: object) -> None:
    handled.append(event.aggregate_id)


def count(model: type) -> int:
    return db.session.scalar(select(func.count()).select_from(model)) or 0


@pytest.mark.usefixtures("app")
def test_event_is_discarded_with_its_rolled_back_transaction() -> None:
    nested = db.session.begin_nested()
    publish_event(db.session, "test.thing_happened", aggregate_type="t", aggregate_id=uuid.uuid4())
    db.session.flush()
    nested.rollback()

    assert count(OutboxEvent) == 0


@pytest.mark.usefixtures("app")
def test_dispatch_creates_one_job_per_handler_exactly_once(clock: FrozenClock) -> None:
    publish_event(db.session, "test.thing_happened", aggregate_type="t", aggregate_id=uuid.uuid4())
    db.session.flush()

    assert dispatch_pending(db.session, now=clock.now()) == 1
    assert dispatch_pending(db.session, now=clock.now()) == 0

    jobs = db.session.scalars(select(Job)).all()
    assert [j.job_type for j in jobs] == [HANDLE_JOB_TYPE]
    assert db.session.scalars(select(OutboxEvent.processed_at)).one() == clock.now()


@pytest.mark.usefixtures("app")
def test_events_without_handlers_are_marked_processed(clock: FrozenClock) -> None:
    publish_event(db.session, "test.unhandled", aggregate_type="t", aggregate_id=uuid.uuid4())
    db.session.flush()

    dispatch_pending(db.session, now=clock.now())

    assert count(Job) == 0
    assert db.session.scalars(select(OutboxEvent.processed_at)).one() is not None


@pytest.mark.usefixtures("app")
def test_worker_delivers_events_to_handlers(clock: FrozenClock) -> None:
    aggregate_id = uuid.uuid4()
    publish_event(db.session, "test.thing_happened", aggregate_type="t", aggregate_id=aggregate_id)
    db.session.commit()
    worker = Worker(session=lambda: db.session, clock=clock, worker_id="w1", schedules=())

    worker.run_once()  # dispatch + run the handler job

    assert aggregate_id in handled
    assert db.session.scalars(select(Job.status)).one() == JobStatus.SUCCEEDED
