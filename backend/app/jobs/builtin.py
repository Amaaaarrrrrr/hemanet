"""Infrastructure jobs. No domain jobs exist until domain phases add them."""

import structlog

from app.core.idempotency import purge_expired
from app.jobs.registry import JobContext, job_handler

log = structlog.get_logger(__name__)

NOOP_JOB_TYPE = "system.noop"


@job_handler(NOOP_JOB_TYPE)
def noop(ctx: JobContext) -> None:
    """Does nothing; used to verify the worker end to end."""
    log.info("noop job executed", job_id=ctx.job_id)


@job_handler("maintenance.purge_expired_idempotency_keys")
def purge_expired_idempotency_keys(ctx: JobContext) -> None:
    removed = purge_expired(ctx.session, ctx.now)
    log.info("expired idempotency keys purged", removed=removed)
