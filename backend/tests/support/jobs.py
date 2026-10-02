"""Test-only job handlers."""

import threading
import uuid

from app.core.outbox import publish_event
from app.jobs.registry import JobContext, job_handler

executions: list[int] = []
_lock = threading.Lock()


@job_handler("test.record")
def record(ctx: JobContext) -> None:
    with _lock:
        executions.append(ctx.job_id)


@job_handler("test.fail")
def fail(ctx: JobContext) -> None:
    raise RuntimeError("downstream failed for donor jane@example.com")


@job_handler("test.emit_then_fail")
def emit_then_fail(ctx: JobContext) -> None:
    publish_event(ctx.session, "test.emitted", aggregate_type="test", aggregate_id=uuid.uuid4())
    ctx.session.flush()
    raise RuntimeError("fail after writing")
