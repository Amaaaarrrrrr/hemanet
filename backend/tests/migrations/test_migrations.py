"""Migration checks (§S.1): upgrade from empty, downgrade/upgrade, model drift."""

from collections.abc import Iterator

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from flask import Flask
from flask_migrate import downgrade, upgrade
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url

from app import create_app
from app.extensions import db
from app.health import migration_heads
from tests.conftest import make_settings, recreate_database, test_database_url

INFRA_TABLES = {"jobs", "outbox_events", "worker_heartbeats", "idempotency_keys"}


@pytest.fixture(scope="module")
def migration_app() -> Iterator[Flask]:
    url = make_url(test_database_url()).set(database="hemanet_migrations_test")
    rendered = url.render_as_string(hide_password=False)
    recreate_database(rendered)
    app = create_app(make_settings(database_url=rendered))
    with app.app_context():
        yield app
        db.engine.dispose()


def tables() -> set[str]:
    return set(inspect(db.engine).get_table_names()) - {"alembic_version"}


def enum_exists() -> bool:
    with db.engine.connect() as conn:
        return bool(conn.scalar(text("SELECT count(*) FROM pg_type WHERE typname = 'job_status'")))


def test_upgrade_from_empty_database(migration_app: Flask) -> None:
    upgrade()

    assert tables() == INFRA_TABLES
    with db.engine.connect() as conn:
        assert {conn.scalar(text("SELECT version_num FROM alembic_version"))} == set(
            migration_heads(migration_app.extensions["migrate"].directory)
        )


def test_downgrade_to_base_and_upgrade_again(migration_app: Flask) -> None:
    upgrade()
    downgrade(revision="base")

    assert tables() == set()
    assert not enum_exists()

    upgrade()
    assert tables() == INFRA_TABLES


def test_models_match_migrations(migration_app: Flask) -> None:
    upgrade()
    with db.engine.connect() as conn:
        context = MigrationContext.configure(
            conn, opts={"compare_type": True, "compare_server_default": True}
        )
        differences = compare_metadata(context, db.metadata)

    assert differences == []


def test_single_migration_head(migration_app: Flask) -> None:
    assert len(migration_heads(migration_app.extensions["migrate"].directory)) == 1
