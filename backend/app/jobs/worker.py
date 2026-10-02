"""The worker loop (``worker`` process, ADR-001/003).

Each iteration: refresh heartbeat (if due) → enqueue scheduled jobs (if due) →
dispatch outbox events → run at most one job. Sleeps ``poll_interval`` when
idle. ``stop()`` (wired to SIGTERM/SIGINT) wakes the sleep immediately; a job
already running finishes before the loop exits. Database outages are logged
and retried; no work is lost because claims and results are transactional.
"""

import os
import socket
import threading
from collections.abc import Callable, Sequence
from datetime import datetime, timedelta

import structlog
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from app.core.clock import Clock
from app.core.db import DbSession
from app.core.ids import new_id
from app.jobs import outbox_dispatch, queue, scheduler
from app.jobs.models import WorkerHeartbeat
from app.jobs.registry import JobContext, PermanentJobError, get_handler

log = structlog.get_logger(__name__)

SCHEDULER_INTERVAL = timedelta(seconds=60)


def default_worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}:{new_id().hex[-8:]}"


class Worker:
    def __init__(
        self,
        *,
        session: Callable[[], DbSession],
        clock: Clock,
        poll_interval: float = 1.0,
        heartbeat_interval: float = 30.0,
        lock_for: timedelta = timedelta(minutes=5),
        schedules: Sequence[scheduler.Schedule] = scheduler.DEFAULT_SCHEDULES,
        worker_id: str | None = None,
    ) -> None:
        self.worker_id = worker_id or default_worker_id()
        self._session = session
        self._clock = clock
        self._poll_interval = poll_interval
        self._heartbeat_interval = timedelta(seconds=heartbeat_interval)
        self._lock_for = lock_for
        self._schedules = schedules
        self._stop = threading.Event()
        self._started_at: datetime | None = None
        self._last_heartbeat: datetime | None = None
        self._last_schedule: datetime | None = None

    # -- lifecycle -----------------------------------------------------------------

    def stop(self) -> None:
        self._stop.set()

    @property
    def stopping(self) -> bool:
        return self._stop.is_set()

    def run_forever(self) -> None:
        log.info("worker started", worker_id=self.worker_id)
        try:
            while not self._stop.is_set():
                try:
                    did_work = self.run_once()
                except SQLAlchemyError as exc:
                    self._session().rollback()
                    log.warning("worker iteration failed", error_type=type(exc).__name__)
                    did_work = False
                if not did_work:
                    self._stop.wait(self._poll_interval)
        finally:
            self._remove_heartbeat()
            log.info("worker stopped", worker_id=self.worker_id)

    # -- one iteration ---------------------------------------------------------------

    def run_once(self) -> bool:
        """Do one round of work. Returns True if anything was processed."""
        self.heartbeat()
        self._run_scheduler()
        dispatched = self.dispatch_outbox()
        ran_job = self.process_next_job()
        return ran_job or dispatched > 0

    def heartbeat(self, force: bool = False) -> None:
        now = self._clock.now()
        if (
            not force
            and self._last_heartbeat is not None
            and now - self._last_heartbeat < self._heartbeat_interval
        ):
            return
        self._started_at = self._started_at or now
        session = self._session()
        stmt = insert(WorkerHeartbeat).values(
            worker_id=self.worker_id, started_at=self._started_at, last_seen_at=now
        )
        session.execute(
            stmt.on_conflict_do_update(
                index_elements=[WorkerHeartbeat.worker_id], set_={"last_seen_at": now}
            )
        )
        session.commit()
        self._last_heartbeat = now

    def _run_scheduler(self) -> None:
        now = self._clock.now()
        if self._last_schedule is not None and now - self._last_schedule < SCHEDULER_INTERVAL:
            return
        session = self._session()
        created = scheduler.enqueue_due(session, self._schedules, now=now)
        session.commit()
        self._last_schedule = now
        if created:
            log.info("scheduled jobs enqueued", count=created)

    def dispatch_outbox(self) -> int:
        session = self._session()
        count = outbox_dispatch.dispatch_pending(session, now=self._clock.now())
        session.commit()
        return count

    def process_next_job(self) -> bool:
        session = self._session()
        claimed = queue.claim_next(
            session, self.worker_id, now=self._clock.now(), lock_for=self._lock_for
        )
        if claimed is None:
            return False
        bound = log.bind(job_id=claimed.id, job_type=claimed.job_type, attempt=claimed.attempt)
        handler = get_handler(claimed.job_type)
        try:
            if handler is None:
                raise PermanentJobError("no handler registered for job type")
            handler(
                JobContext(
                    job_id=claimed.id,
                    job_type=claimed.job_type,
                    payload=claimed.payload,
                    attempt=claimed.attempt,
                    session=session,
                    now=self._clock.now(),
                )
            )
            queue.mark_succeeded(session, claimed.id, self.worker_id, now=self._clock.now())
            session.commit()
            bound.info("job succeeded")
        except Exception as exc:
            session.rollback()
            status = queue.mark_failed(
                session,
                claimed.id,
                self.worker_id,
                now=self._clock.now(),
                error=exc,
                permanent=isinstance(exc, PermanentJobError),
            )
            session.commit()
            bound.warning("job failed", status=status, error=queue.describe_error(exc))
        return True

    def _remove_heartbeat(self) -> None:
        try:
            session = self._session()
            session.rollback()
            session.execute(
                delete(WorkerHeartbeat).where(WorkerHeartbeat.worker_id == self.worker_id)
            )
            session.commit()
        except SQLAlchemyError as exc:
            log.warning("could not remove worker heartbeat", error_type=type(exc).__name__)
