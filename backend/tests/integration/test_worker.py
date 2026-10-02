"""Worker loop: processing, failures, scheduler, heartbeat, stop."""

import threading
import time
from collections.abc import Callable
from datetime import timedelta

import pytest
from flask import Flask
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError

from app.core.clock import FrozenClock
from app.core.outbox import OutboxEvent
from app.extensions import db
from app.jobs import queue
from app.jobs.builtin import NOOP_JOB_TYPE
from app.jobs.models import Job, JobStatus, WorkerHeartbeat
from app.jobs.scheduler import DEFAULT_SCHEDULES
from app.jobs.worker import Worker


def make_worker(clock: FrozenClock, worker_id: str = "w1", **kwargs: object) -> Worker:
    return Worker(session=lambda: db.session, clock=clock, worker_id=worker_id, **kwargs)  # type: ignore[arg-type]


def status_of(job_id: int) -> JobStatus:
    db.session.expire_all()
    return db.session.get_one(Job, job_id).status


@pytest.mark.usefixtures("app")
def test_processes_a_noop_job(clock: FrozenClock) -> None:
    job_id = queue.enqueue(db.session, NOOP_JOB_TYPE, now=clock.now())
    assert job_id is not None

    assert make_worker(clock).run_once()

    assert status_of(job_id) == JobStatus.SUCCEEDED


@pytest.mark.usefixtures("app")
def test_failed_handler_schedules_retry_with_redacted_error(clock: FrozenClock) -> None:
    job_id = queue.enqueue(db.session, "test.fail", now=clock.now())
    assert job_id is not None

    make_worker(clock).run_once()

    row = db.session.get_one(Job, job_id)
    assert row.status == JobStatus.FAILED
    assert row.last_error == "RuntimeError: downstream failed for donor [REDACTED]"


@pytest.mark.usefixtures("app")
def test_handler_writes_are_rolled_back_on_failure(clock: FrozenClock) -> None:
    queue.enqueue(db.session, "test.emit_then_fail", now=clock.now())

    make_worker(clock).run_once()

    assert db.session.scalar(select(func.count()).select_from(OutboxEvent)) == 0


@pytest.mark.usefixtures("app")
def test_job_without_handler_goes_dead(clock: FrozenClock) -> None:
    orphan = Job(job_type="removed.type", run_at=clock.now(), payload={})
    db.session.add(orphan)
    db.session.flush()

    make_worker(clock).run_once()

    assert status_of(orphan.id) == JobStatus.DEAD


@pytest.mark.usefixtures("app")
def test_heartbeat_is_written_and_refreshed_on_interval(clock: FrozenClock) -> None:
    worker = make_worker(clock, heartbeat_interval=30)
    worker.run_once()
    first = db.session.get_one(WorkerHeartbeat, "w1").last_seen_at

    clock.advance(timedelta(seconds=10))
    worker.run_once()
    db.session.expire_all()
    assert db.session.get_one(WorkerHeartbeat, "w1").last_seen_at == first

    clock.advance(timedelta(seconds=25))
    worker.run_once()
    db.session.expire_all()
    assert db.session.get_one(WorkerHeartbeat, "w1").last_seen_at == clock.now()


@pytest.mark.usefixtures("app")
def test_scheduler_enqueues_each_slot_once_across_workers(clock: FrozenClock) -> None:
    make_worker(clock, "w1").heartbeat()
    for worker in (make_worker(clock, "w1"), make_worker(clock, "w2")):
        worker._run_scheduler()

    scheduled = db.session.scalars(
        select(Job).where(Job.job_type == DEFAULT_SCHEDULES[0].job_type)
    ).all()
    assert len(scheduled) == 1
    assert scheduled[0].dedupe_key and scheduled[0].dedupe_key.startswith("schedule:")


def run_in_thread(app: Flask, target: Callable[[], None]) -> threading.Thread:
    def body() -> None:
        with app.app_context():
            target()

    thread = threading.Thread(target=body)
    thread.start()
    return thread


@pytest.mark.concurrency
def test_stop_returns_promptly_and_removes_heartbeat(real_app: Flask, clock: FrozenClock) -> None:
    worker = Worker(session=lambda: db.session, clock=clock, poll_interval=30, worker_id="stopper")
    thread = run_in_thread(real_app, worker.run_forever)
    deadline = time.monotonic() + 5
    while db.session.get(WorkerHeartbeat, "stopper") is None and time.monotonic() < deadline:
        db.session.expire_all()
        time.sleep(0.05)

    started = time.monotonic()
    worker.stop()
    thread.join(timeout=5)

    assert not thread.is_alive()
    assert time.monotonic() - started < 2  # does not wait out the 30 s poll interval
    db.session.expire_all()
    assert db.session.get(WorkerHeartbeat, "stopper") is None


@pytest.mark.concurrency
def test_survives_a_database_error(
    real_app: Flask, clock: FrozenClock, monkeypatch: pytest.MonkeyPatch
) -> None:
    job_id = queue.enqueue(db.session, NOOP_JOB_TYPE, now=clock.now())
    db.session.commit()
    real_claim = queue.claim_next
    calls = {"n": 0}

    def flaky_claim(*args: object, **kwargs: object) -> object:
        calls["n"] += 1
        if calls["n"] == 1:
            raise OperationalError("SELECT", {}, ConnectionResetError("server closed"))
        return real_claim(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(queue, "claim_next", flaky_claim)
    worker = Worker(session=lambda: db.session, clock=clock, poll_interval=0.01, worker_id="flaky")
    thread = run_in_thread(real_app, worker.run_forever)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        db.session.expire_all()
        if db.session.get_one(Job, job_id).status == JobStatus.SUCCEEDED:
            break
        time.sleep(0.05)
    worker.stop()
    thread.join(timeout=5)

    assert calls["n"] >= 2
    assert db.session.get_one(Job, job_id).status == JobStatus.SUCCEEDED
