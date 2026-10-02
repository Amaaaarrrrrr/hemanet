"""Genuinely concurrent sessions: two workers never claim the same job (ADR-003)."""

import threading
from datetime import timedelta

import pytest
from flask import Flask
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import FrozenClock
from app.extensions import db
from app.jobs import queue
from app.jobs.models import Job, JobStatus
from app.jobs.worker import Worker
from tests.support import jobs as test_jobs

pytestmark = pytest.mark.concurrency
LOCK = timedelta(minutes=5)


def enqueue_many(clock: FrozenClock, count: int, job_type: str = "test.record") -> list[int]:
    ids = [queue.enqueue(db.session, job_type, now=clock.now()) for _ in range(count)]
    db.session.commit()
    return [i for i in ids if i is not None]


def test_skip_locked_hands_a_locked_job_to_nobody_else(real_app: Flask, clock: FrozenClock) -> None:
    first, second = enqueue_many(clock, 2)
    holder = Session(db.engine)
    other = Session(db.engine)
    try:
        # Session A locks the first job and keeps its transaction open.
        locked = holder.scalars(
            select(Job).where(Job.id == first).with_for_update(skip_locked=True)
        ).one()
        assert locked.id == first

        claimed = queue.claim_next(other, "w2", now=clock.now(), lock_for=LOCK)

        assert claimed is not None and claimed.id == second
        assert queue.claim_next(other, "w2", now=clock.now(), lock_for=LOCK) is None
    finally:
        holder.rollback()
        holder.close()
        other.close()


def test_parallel_claimers_never_share_a_job(real_app: Flask, clock: FrozenClock) -> None:
    job_ids = enqueue_many(clock, 60)
    claims: list[list[int]] = [[] for _ in range(8)]
    barrier = threading.Barrier(8)
    engine = db.engine  # threads have no Flask app context

    def claimer(slot: int) -> None:
        session = Session(engine)
        barrier.wait()
        try:
            while job := queue.claim_next(session, f"w{slot}", now=clock.now(), lock_for=LOCK):
                claims[slot].append(job.id)
        finally:
            session.close()

    threads = [threading.Thread(target=claimer, args=(i,)) for i in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    all_claims = [job_id for chunk in claims for job_id in chunk]
    assert sorted(all_claims) == sorted(job_ids)  # every job claimed exactly once
    assert sum(1 for chunk in claims if chunk) > 1  # work really was spread out


def test_two_workers_run_each_job_exactly_once(real_app: Flask, clock: FrozenClock) -> None:
    test_jobs.executions.clear()
    job_ids = enqueue_many(clock, 40)
    barrier = threading.Barrier(2)
    engine = db.engine

    def run_worker(name: str) -> None:
        session = Session(engine)
        worker = Worker(session=lambda: session, clock=clock, worker_id=name, schedules=())
        barrier.wait()
        try:
            while worker.process_next_job():
                pass
        finally:
            session.close()

    threads = [threading.Thread(target=run_worker, args=(n,)) for n in ("a", "b")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert sorted(test_jobs.executions) == sorted(job_ids)
    statuses = db.session.scalars(select(Job.status)).all()
    assert statuses == [JobStatus.SUCCEEDED] * 40
