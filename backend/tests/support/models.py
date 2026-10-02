"""Test-only model on a separate metadata (never part of migrations or drift checks)."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, MetaData, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, registry

from app.core.db import TimestampMixin, UUIDPrimaryKeyMixin, VersionMixin


class TestBase(DeclarativeBase):
    __test__ = False  # not a pytest test class
    registry = registry(
        metadata=MetaData(),
        type_annotation_map={
            datetime: DateTime(timezone=True),
            uuid.UUID: Uuid(as_uuid=True),
            dict[str, Any]: JSONB,
        },
    )


class Widget(UUIDPrimaryKeyMixin, TimestampMixin, VersionMixin, TestBase):
    __tablename__ = "test_widgets"

    name: Mapped[str] = mapped_column(String(100))
