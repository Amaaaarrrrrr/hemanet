"""Outbox dispatch: turns committed outbox events into handler jobs.

Each (event, handler) pair becomes an ``outbox.handle`` job with a dedupe key,
so handler failures reuse the job queue's retry/backoff/DEAD handling and a
handler never runs twice for the same event. Delivery is at-least-once:
handlers must be idempotent.
"""

from collections.abc import Callable
from datetime import datetime

from sqlalchemy import select

from app.core.db import DbSession
from app.core.outbox import OutboxEvent
from app.jobs.queue import enqueue
from app.jobs.registry import JobContext, PermanentJobError, job_handler

EventHandler = Callable[[OutboxEvent, DbSession], None]
HANDLE_JOB_TYPE = "outbox.handle"

_event_handlers: dict[str, dict[str, EventHandler]] = {}


def event_handler(event_type: str, name: str) -> Callable[[EventHandler], EventHandler]:
    def register(fn: EventHandler) -> EventHandler:
        handlers = _event_handlers.setdefault(event_type, {})
        if name in handlers and handlers[name] is not fn:
            raise ValueError(f"duplicate outbox handler {name!r} for {event_type!r}")
        handlers[name] = fn
        return fn

    return register


def dispatch_pending(session: DbSession, *, now: datetime, batch_size: int = 100) -> int:
    """Fan out a batch of unprocessed events into jobs. Caller commits. Returns count."""
    events = session.scalars(
        select(OutboxEvent)
        .where(OutboxEvent.processed_at.is_(None))
        .order_by(OutboxEvent.id)
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    ).all()
    for event in events:
        for name in sorted(_event_handlers.get(event.event_type, {})):
            enqueue(
                session,
                HANDLE_JOB_TYPE,
                {"event_id": event.id, "handler": name},
                now=now,
                dedupe_key=f"outbox:{event.id}:{name}",
            )
        event.processed_at = now
        event.attempts += 1
    return len(events)


@job_handler(HANDLE_JOB_TYPE)
def _handle_event(ctx: JobContext) -> None:
    event = ctx.session.get(OutboxEvent, ctx.payload["event_id"])
    if event is None:
        raise PermanentJobError("outbox event not found")
    handler = _event_handlers.get(event.event_type, {}).get(str(ctx.payload["handler"]))
    if handler is None:
        raise PermanentJobError("outbox handler no longer registered")
    handler(event, ctx.session)
