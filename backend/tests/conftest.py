"""Shared fixtures.

Tests run against a real PostgreSQL database (never SQLite, blueprint §S.1)
named by ``TEST_DATABASE_URL``; its name must end in ``_test`` because the
database is dropped and recreated at the start of every run.

* ``app``/``client``: each test runs inside a transaction that is rolled back
  (code under test may commit; commits become savepoint releases).
* ``real_app``: real commits for tests that need genuinely concurrent sessions;
  tables are truncated afterwards.
"""

import os
import re
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from flask import Flask
from flask.testing import FlaskClient
from flask_migrate import upgrade
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import scoped_session, sessionmaker

from app import create_app
from app.config import Settings, load_settings
from app.core.clock import FrozenClock
from app.extensions import api, db
from tests.support import jobs as _test_jobs  # noqa: F401  (registers test job types)
from tests.support.models import TestBase
from tests.support.routes import blp as test_blp

START = datetime(2026, 10, 2, 9, 0, tzinfo=UTC)
TRUNCATE_TABLES = "jobs, outbox_events, worker_heartbeats, idempotency_keys, test_widgets"
_DB_NAME = re.compile(r"^[a-z0-9_]+_test$")


def test_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.exit("TEST_DATABASE_URL is not set. Run `make test` (see README).", returncode=2)
    if not _DB_NAME.fullmatch(make_url(url).database or ""):
        pytest.exit("Refusing to run: the TEST_DATABASE_URL database must end in _test.", 2)
    return url


test_database_url.__test__ = False  # type: ignore[attr-defined]


def recreate_database(url: str) -> None:
    parsed = make_url(url)
    name = parsed.database or ""
    if not _DB_NAME.fullmatch(name):
        raise ValueError("test database names must end in _test")
    admin = create_engine(parsed.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    admin.dispose()


def make_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "app_env": "ci",
        "database_url": test_database_url(),
        "log_format": "console",
        "cors_allowed_origins": "http://localhost:5173",
    }
    values.update(overrides)
    return load_settings(**values)


def build_app(clock: FrozenClock, **overrides: object) -> Flask:
    app = create_app(make_settings(**overrides), clock=clock)
    api.register_blueprint(test_blp)
    return app


@pytest.fixture(scope="session")
def migrated_database() -> str:
    url = test_database_url()
    recreate_database(url)
    app = create_app(make_settings())
    with app.app_context():
        upgrade()
        TestBase.metadata.create_all(db.engine)
        db.engine.dispose()
    return url


@pytest.fixture
def clock() -> FrozenClock:
    return FrozenClock(START)


@pytest.fixture
def app(migrated_database: str, clock: FrozenClock) -> Iterator[Flask]:
    app = build_app(clock)
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
        original_session = db.session
        # A plain SQLAlchemy session bound to the test connection. (Flask-SQLAlchemy's
        # own session class resolves binds from model metadata and would bypass it.)
        # Commits by code under test become SAVEPOINT releases inside this transaction.
        db.session = cast(
            "Any",
            scoped_session(sessionmaker(bind=connection, join_transaction_mode="create_savepoint")),
        )
        try:
            yield app
        finally:
            db.session.remove()
            db.session = original_session
            transaction.rollback()
            connection.close()
            db.engine.dispose()


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()


@pytest.fixture
def real_app(migrated_database: str, clock: FrozenClock) -> Iterator[Flask]:
    app = build_app(clock)
    with app.app_context():
        try:
            yield app
        finally:
            db.session.remove()
            with db.engine.begin() as conn:
                conn.execute(text(f"TRUNCATE {TRUNCATE_TABLES} RESTART IDENTITY"))
            db.engine.dispose()
