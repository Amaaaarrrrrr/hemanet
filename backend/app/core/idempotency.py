"""Idempotency keys for critical POSTs (blueprint §N.1 "Idempotency", §E.10).

Usage on a view (from E2 onwards, once a principal exists)::

    @idempotent(principal=current_user_id)
    def create_thing(): ...

Semantics:

* ``Idempotency-Key`` header required (8-255 printable ASCII characters).
* Keys are scoped per principal. A replay with the same method, path and body
  within the TTL (24 h) returns the stored response with
  ``Idempotent-Replayed: true``; the view does not run again.
* The same key with a different request gives 409 ``IDEMPOTENCY_KEY_REUSED``.
* Only successful (2xx) responses are stored. If the view raises or returns an
  error, the key is released so the client can retry.
* A concurrent duplicate blocks on the key's unique index until the first
  request commits, then replays it.
* The decorator owns the transaction: it commits the view's work together with
  the stored response.

Staged migration (documented in docs/backend-foundation.md): ``user_id`` has no
foreign key yet because the ``users`` table arrives in E2; E2 adds it.
"""

import hashlib
import re
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
from functools import wraps
from typing import Any

from flask import Response, current_app, jsonify, make_response, request
from sqlalchemy import CheckConstraint, Index, Integer, String, delete, select
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.core.db import Base, DbSession
from app.core.errors import Conflict, IdempotencyKeyReused, ValidationFailed

IDEMPOTENCY_HEADER = "Idempotency-Key"
REPLAYED_HEADER = "Idempotent-Replayed"
DEFAULT_TTL = timedelta(hours=24)
_VALID_KEY = re.compile(r"^[\x21-\x7e]{8,255}$")


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    __table_args__ = (
        CheckConstraint("char_length(key) BETWEEN 8 AND 255", name="key_length"),
        Index("ix_idempotency_keys_expires_at", "expires_at"),
    )

    # No FK yet: users table arrives in E2 (staged migration, see module docstring).
    user_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    endpoint: Mapped[str] = mapped_column(String(200))
    request_hash: Mapped[str] = mapped_column(String(64))
    response_status: Mapped[int | None] = mapped_column(Integer)
    response_body: Mapped[Any | None] = mapped_column(JSONB)
    created_at: Mapped[datetime]
    expires_at: Mapped[datetime]


def request_fingerprint(method: str, path: str, body: bytes) -> str:
    digest = hashlib.sha256()
    for part in (method.encode(), b"\n", path.encode(), b"\n", body):
        digest.update(part)
    return digest.hexdigest()


def purge_expired(session: DbSession, now: datetime) -> int:
    result = session.execute(delete(IdempotencyKey).where(IdempotencyKey.expires_at <= now))
    return int(getattr(result, "rowcount", 0) or 0)


def _ttl() -> timedelta:
    hours = current_app.config.get("IDEMPOTENCY_TTL_HOURS")
    return timedelta(hours=hours) if hours else DEFAULT_TTL


def idempotent(
    principal: Callable[[], uuid.UUID],
    session_getter: Callable[[], DbSession] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Response]]:
    def decorator(view: Callable[..., Any]) -> Callable[..., Response]:
        @wraps(view)
        def wrapper(*args: Any, **kwargs: Any) -> Response:
            session = session_getter() if session_getter else _default_session()
            key = request.headers.get(IDEMPOTENCY_HEADER)
            if key is None or not _VALID_KEY.fullmatch(key):
                raise ValidationFailed(
                    "A valid Idempotency-Key header is required for this request.",
                    details=[
                        {
                            "field": IDEMPOTENCY_HEADER,
                            "issue": "required" if key is None else "invalid",
                        }
                    ],
                )
            user_id = principal()
            endpoint = request.endpoint or request.path
            fingerprint = request_fingerprint(request.method, request.path, request.get_data())
            now = utcnow()

            if not _claim(session, user_id, key, endpoint, fingerprint, now):
                existing = session.execute(
                    select(IdempotencyKey).where(
                        IdempotencyKey.user_id == user_id, IdempotencyKey.key == key
                    )
                ).scalar_one()
                if existing.expires_at <= now:
                    session.delete(existing)
                    session.flush()
                    if not _claim(session, user_id, key, endpoint, fingerprint, now):
                        raise Conflict("A request with this Idempotency-Key is in progress.")
                else:
                    return _replay(session, existing, endpoint, fingerprint)

            try:
                response = make_response(view(*args, **kwargs))
            except BaseException:
                session.rollback()
                raise
            if 200 <= response.status_code < 300 and response.is_json:
                record = session.get(IdempotencyKey, (user_id, key))
                if record is not None:
                    record.response_status = response.status_code
                    record.response_body = response.get_json()
                session.commit()
            else:
                session.rollback()
            return response

        return wrapper

    return decorator


def _default_session() -> DbSession:
    session: DbSession = current_app.extensions["sqlalchemy"].session
    return session


def _claim(
    session: DbSession, user_id: uuid.UUID, key: str, endpoint: str, fingerprint: str, now: datetime
) -> bool:
    stmt = (
        insert(IdempotencyKey)
        .values(
            user_id=user_id,
            key=key,
            endpoint=endpoint,
            request_hash=fingerprint,
            created_at=now,
            expires_at=now + _ttl(),
        )
        .on_conflict_do_nothing()
        .returning(IdempotencyKey.key)
    )
    return session.execute(stmt).scalar_one_or_none() is not None


def _replay(
    session: DbSession, existing: IdempotencyKey, endpoint: str, fingerprint: str
) -> Response:
    if existing.endpoint != endpoint or existing.request_hash != fingerprint:
        session.rollback()
        raise IdempotencyKeyReused()
    if existing.response_status is None:
        session.rollback()
        raise Conflict("A request with this Idempotency-Key is still being processed.")
    response = jsonify(existing.response_body)
    response.status_code = existing.response_status
    response.headers[REPLAYED_HEADER] = "true"
    session.rollback()
    return response
