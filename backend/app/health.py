"""Liveness and readiness probes (blueprint §N.2 "Ops").

* ``GET /healthz``: the process is up. Never touches the database.
* ``GET /readyz``: database reachable, migrations at head, worker heartbeat
  fresh. Responses are generic (``ready`` / ``not_ready``); which check failed
  is logged server-side only.

Served at the root, not under ``/api/v1``: they are operational endpoints, not
part of the versioned API.
"""

from datetime import datetime, timedelta
from pathlib import Path

import structlog
from alembic.config import Config
from alembic.script import ScriptDirectory
from flask import Response, current_app, jsonify
from marshmallow import Schema, fields
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.core.api import Blueprint
from app.core.clock import utcnow
from app.core.db import DbSession
from app.extensions import db
from app.jobs.models import WorkerHeartbeat

log = structlog.get_logger(__name__)

blp = Blueprint("health", __name__, description="Liveness and readiness probes")

MIGRATIONS_DIR_KEY = "hemanet.migrations_dir"
_HEADS_CACHE_KEY = "hemanet.migration_heads"


class StatusSchema(Schema):
    status = fields.String(required=True)


def migration_heads(migrations_dir: Path) -> frozenset[str]:
    config = Config()
    config.set_main_option("script_location", str(migrations_dir))
    return frozenset(ScriptDirectory.from_config(config).get_heads())


def expected_heads() -> frozenset[str]:
    """Head revision(s) of the deployed migration scripts, read once per process."""
    heads: frozenset[str] | None = current_app.extensions.get(_HEADS_CACHE_KEY)
    if heads is None:
        heads = migration_heads(current_app.extensions[MIGRATIONS_DIR_KEY])
        current_app.extensions[_HEADS_CACHE_KEY] = heads
    return heads


def readiness_failures(
    session: DbSession, *, now: datetime, expected_heads: frozenset[str], max_age: timedelta
) -> list[str]:
    failures: list[str] = []
    try:
        session.execute(text("SET LOCAL statement_timeout = '2s'"))
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        session.rollback()
        return ["database"]
    try:
        current = frozenset(session.scalars(text("SELECT version_num FROM alembic_version")))
        if current != expected_heads:
            failures.append("migrations")
        last_seen = session.scalar(select(func.max(WorkerHeartbeat.last_seen_at)))
        if last_seen is None or last_seen < now - max_age:
            failures.append("worker_heartbeat")
    except SQLAlchemyError:
        failures.append("migrations")
    finally:
        session.rollback()
    return failures


@blp.route("/healthz")
@blp.response(200, StatusSchema)
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@blp.route("/readyz")
@blp.response(200, StatusSchema)
@blp.alt_response(503, schema=StatusSchema, description="Not ready")
def readyz() -> Response:
    settings = get_settings()
    failures = readiness_failures(
        db.session,
        now=utcnow(),
        expected_heads=expected_heads(),
        max_age=timedelta(seconds=settings.readiness_heartbeat_max_age_seconds),
    )
    if failures:
        log.warning("readiness check failed", failed_checks=failures)
        response = jsonify({"status": "not_ready"})
        response.status_code = 503
        return response
    return jsonify({"status": "ready"})
