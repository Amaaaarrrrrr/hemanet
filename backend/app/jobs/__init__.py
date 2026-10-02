"""Background work: job registry, queue, scheduler and worker loop (ADR-003)."""


def load_job_handlers() -> None:
    """Import every module that registers job or outbox handlers."""
    from app.jobs import builtin, outbox_dispatch  # noqa: F401
