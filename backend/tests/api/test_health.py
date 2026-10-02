"""``/healthz`` and ``/readyz`` (§N.2): generic bodies, real checks."""

from datetime import timedelta

import pytest
from flask.testing import FlaskClient
from sqlalchemy import text

from app import create_app
from app.core.clock import FrozenClock
from app.extensions import db
from app.jobs.models import WorkerHeartbeat
from tests.conftest import START, make_settings


def beat(clock: FrozenClock, worker_id: str = "w1") -> None:
    db.session.add(
        WorkerHeartbeat(worker_id=worker_id, started_at=clock.now(), last_seen_at=clock.now())
    )
    db.session.flush()


def test_healthz_is_ok(client: FlaskClient) -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_ready_with_database_migrations_and_fresh_heartbeat(
    client: FlaskClient, clock: FrozenClock
) -> None:
    beat(clock)

    response = client.get("/readyz")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ready"}


def test_not_ready_without_any_worker_heartbeat(
    client: FlaskClient, capsys: pytest.CaptureFixture[str]
) -> None:
    response = client.get("/readyz")

    assert response.status_code == 503
    assert response.get_json() == {"status": "not_ready"}  # no internal details
    assert "worker_heartbeat" in capsys.readouterr().out  # reason logged server-side


def test_not_ready_when_heartbeat_is_stale(client: FlaskClient, clock: FrozenClock) -> None:
    beat(clock)
    clock.advance(timedelta(seconds=121))

    assert client.get("/readyz").status_code == 503


def test_not_ready_when_migrations_are_not_at_head(
    client: FlaskClient, clock: FrozenClock, capsys: pytest.CaptureFixture[str]
) -> None:
    beat(clock)
    db.session.execute(text("UPDATE alembic_version SET version_num = 'old'"))

    response = client.get("/readyz")

    assert response.status_code == 503
    assert response.get_json() == {"status": "not_ready"}
    assert "migrations" in capsys.readouterr().out


def test_not_ready_when_database_is_unreachable(migrated_database: str) -> None:
    settings = make_settings(
        database_url="postgresql+psycopg://hemanet:x@127.0.0.1:1/unreachable_test"
    )
    app = create_app(settings, clock=FrozenClock(START))

    response = app.test_client().get("/readyz")

    assert response.status_code == 503
    assert response.get_json() == {"status": "not_ready"}
    assert b"127.0.0.1" not in response.data
