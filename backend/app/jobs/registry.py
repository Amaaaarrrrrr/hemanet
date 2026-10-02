"""Registry of job handlers. Handlers are plain functions taking a ``JobContext``."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.core.db import DbSession


class PermanentJobError(Exception):
    """Raise from a handler when retrying cannot help; the job goes straight to DEAD."""


@dataclass(frozen=True)
class JobContext:
    job_id: int
    job_type: str
    payload: Mapping[str, Any]
    attempt: int
    session: DbSession
    now: datetime


JobHandler = Callable[[JobContext], None]

_handlers: dict[str, JobHandler] = {}


def job_handler(job_type: str) -> Callable[[JobHandler], JobHandler]:
    def register(fn: JobHandler) -> JobHandler:
        if job_type in _handlers and _handlers[job_type] is not fn:
            raise ValueError(f"duplicate job handler for {job_type!r}")
        _handlers[job_type] = fn
        return fn

    return register


def get_handler(job_type: str) -> JobHandler | None:
    return _handlers.get(job_type)


def registered_job_types() -> frozenset[str]:
    return frozenset(_handlers)
