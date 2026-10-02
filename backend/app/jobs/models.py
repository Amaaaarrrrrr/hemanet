"""Job queue and worker heartbeat tables (ADR-003, blueprint §E.10)."""

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Enum,
    Identity,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin


class JobStatus(enum.StrEnum):
    QUEUED = "QUEUED"  # waiting for run_at
    RUNNING = "RUNNING"  # claimed by a worker until locked_until
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"  # an attempt failed; retry scheduled at run_at
    DEAD = "DEAD"  # attempts exhausted or permanent failure; needs a human


class Job(TimestampMixin, Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint("attempts >= 0", name="attempts_non_negative"),
        CheckConstraint("max_attempts >= 1", name="max_attempts_positive"),
        Index(
            "ix_jobs_claimable",
            "run_at",
            "id",
            postgresql_where=text("status IN ('QUEUED', 'FAILED')"),
        ),
        Index(
            "ix_jobs_running_locked_until",
            "locked_until",
            postgresql_where=text("status = 'RUNNING'"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    job_type: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    run_at: Mapped[datetime]
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status", values_callable=lambda e: [m.value for m in e]),
        default=JobStatus.QUEUED,
        server_default=JobStatus.QUEUED.value,
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    max_attempts: Mapped[int] = mapped_column(Integer, default=5, server_default="5")
    locked_by: Mapped[str | None] = mapped_column(String(200))
    locked_until: Mapped[datetime | None]
    last_error: Mapped[str | None] = mapped_column(Text)
    dedupe_key: Mapped[str | None] = mapped_column(String(255), unique=True)


class WorkerHeartbeat(Base):
    """One row per live worker process; used by ``/readyz``."""

    __tablename__ = "worker_heartbeats"

    worker_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    started_at: Mapped[datetime]
    last_seen_at: Mapped[datetime] = mapped_column(index=True)
