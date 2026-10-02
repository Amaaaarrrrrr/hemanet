"""Transactional outbox (ADR-003, blueprint §E.10).

``publish_event`` adds an event to the *caller's* session, so the event is
committed atomically with the state change that caused it (or not at all).
The worker dispatches committed events to registered handlers.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Identity, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.core.db import Base, DbSession


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    __table_args__ = (
        Index(
            "ix_outbox_events_unprocessed",
            "id",
            postgresql_where=text("processed_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(100))
    aggregate_type: Mapped[str] = mapped_column(String(100))
    aggregate_id: Mapped[uuid.UUID]
    payload: Mapped[dict[str, Any]]
    occurred_at: Mapped[datetime]
    processed_at: Mapped[datetime | None]
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_error: Mapped[str | None] = mapped_column(Text)


def publish_event(
    session: DbSession,
    event_type: str,
    *,
    aggregate_type: str,
    aggregate_id: uuid.UUID,
    payload: dict[str, Any] | None = None,
) -> OutboxEvent:
    """Record a domain event in the current transaction. Payloads must not contain PHI."""
    event = OutboxEvent(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        payload=payload or {},
        occurred_at=utcnow(),
    )
    session.add(event)
    return event
