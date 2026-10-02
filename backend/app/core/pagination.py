"""Cursor (keyset) pagination (blueprint §N.1 "Pagination").

Lists are returned as ``{"data": [...], "page": {"next_cursor": ..., "limit": n}}``.
Cursors are opaque to clients: base64url-encoded, versioned, typed JSON of the
last row's sort-key values. A cursor is not a security boundary: it only moves
a position *within* a query whose scope the caller already restricted.
"""

import base64
import binascii
import json
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from marshmallow import Schema, fields, validate
from sqlalchemy import Select, tuple_
from sqlalchemy.orm import InstrumentedAttribute

from app.core.db import DbSession
from app.core.errors import ValidationFailed

DEFAULT_LIMIT = 25
MAX_LIMIT = 100
_CURSOR_VERSION = 1


class PageArgsSchema(Schema):
    """Query arguments shared by every list endpoint (unknown params are rejected)."""

    limit = fields.Integer(
        load_default=DEFAULT_LIMIT, validate=validate.Range(min=1, max=MAX_LIMIT)
    )
    cursor = fields.String(load_default=None, validate=validate.Length(max=512))


@dataclass(frozen=True)
class Page[T]:
    items: list[T]
    next_cursor: str | None
    limit: int

    def envelope(self, serialize: Callable[[T], Any]) -> dict[str, Any]:
        return {
            "data": [serialize(item) for item in self.items],
            "page": {"next_cursor": self.next_cursor, "limit": self.limit},
        }


def _encode_value(value: Any) -> list[Any]:
    if isinstance(value, datetime):
        return ["dt", value.isoformat()]
    if isinstance(value, uuid.UUID):
        return ["uuid", str(value)]
    if isinstance(value, bool) or value is None:
        raise TypeError("unsupported cursor value")
    if isinstance(value, int):
        return ["int", value]
    if isinstance(value, str):
        return ["str", value]
    raise TypeError(f"unsupported cursor value type: {type(value).__name__}")


def _decode_value(item: Any) -> Any:
    match item:
        case ["dt", str(text)]:
            parsed = datetime.fromisoformat(text)
            if parsed.tzinfo is None:
                raise ValueError("naive datetime")
            return parsed
        case ["uuid", str(text)]:
            return uuid.UUID(text)
        case ["int", int(number)] if not isinstance(number, bool):
            return number
        case ["str", str(text)]:
            return text
    raise ValueError("bad cursor value")


def encode_cursor(values: Sequence[Any]) -> str:
    payload = json.dumps(
        {"v": _CURSOR_VERSION, "k": [_encode_value(v) for v in values]}, separators=(",", ":")
    )
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")


def decode_cursor(cursor: str, expected_length: int) -> list[Any]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode()))
        if payload.get("v") != _CURSOR_VERSION:
            raise ValueError("unsupported cursor version")
        values = [_decode_value(item) for item in payload["k"]]
        if len(values) != expected_length:
            raise ValueError("cursor shape mismatch")
        return values
    except (ValueError, KeyError, TypeError, AttributeError, binascii.Error) as exc:
        raise ValidationFailed(
            "The pagination cursor is invalid.",
            details=[{"field": "cursor", "issue": "invalid"}],
        ) from exc


def paginate[T](
    session: DbSession,
    stmt: Select[T],
    *,
    order_by: Sequence[InstrumentedAttribute[Any]],
    limit: int,
    cursor: str | None,
    descending: bool = False,
) -> Page[T]:
    """Keyset-paginate ``stmt``.

    ``order_by`` must end with a unique column (normally ``id``) so the order
    is total. All columns sort in the same direction.
    """
    if not order_by:
        raise ValueError("order_by must not be empty")
    if not 1 <= limit <= MAX_LIMIT:
        raise ValueError("limit out of range")
    columns = list(order_by)
    if cursor is not None:
        position = decode_cursor(cursor, len(columns))
        key = tuple_(*columns)
        stmt = stmt.where(key < tuple_(*position) if descending else key > tuple_(*position))
    stmt = stmt.order_by(*(c.desc() if descending else c.asc() for c in columns))
    rows: list[T] = list(session.scalars(stmt.limit(limit + 1)))
    items = rows[:limit]
    next_cursor = None
    if len(rows) > limit and items:
        last = items[-1]
        next_cursor = encode_cursor([getattr(last, c.key) for c in columns])
    return Page(items=items, next_cursor=next_cursor, limit=limit)
