"""HemaNet API application factory (backlog E1.1)."""

from pathlib import Path

from flask import Flask

from app.config import SETTINGS_EXTENSION_KEY, Settings, load_settings
from app.core.clock import CLOCK_EXTENSION_KEY, Clock, SystemClock
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.core.request_context import REQUEST_ID_HEADER, init_request_context
from app.core.security_headers import init_security_headers
from app.extensions import api, cors, db, migrate

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def create_app(settings: Settings | None = None, *, clock: Clock | None = None) -> Flask:
    settings = settings or load_settings()
    configure_logging(settings.log_level, settings.log_format)

    app = Flask(__name__)
    app.config.update(
        SQLALCHEMY_DATABASE_URI=settings.database_url.get_secret_value(),
        SQLALCHEMY_ENGINE_OPTIONS={
            "pool_pre_ping": True,
            "pool_size": settings.db_pool_size,
            "connect_args": {"connect_timeout": 3},
        },
        MAX_CONTENT_LENGTH=settings.max_content_length_bytes,
        IDEMPOTENCY_TTL_HOURS=settings.idempotency_ttl_hours,
        API_TITLE="HemaNet API",
        API_VERSION="v1",
        OPENAPI_VERSION="3.1.0",
        OPENAPI_URL_PREFIX="/api/v1" if settings.expose_openapi else None,
        OPENAPI_JSON_PATH="openapi.json",
    )
    app.extensions[SETTINGS_EXTENSION_KEY] = settings
    app.extensions[CLOCK_EXTENSION_KEY] = clock or SystemClock()

    from app import models  # noqa: F401  (register all tables on the metadata)
    from app.health import MIGRATIONS_DIR_KEY
    from app.health import blp as health_blp
    from app.jobs import load_job_handlers
    from app.jobs.cli import register_cli

    db.init_app(app)
    migrate.init_app(app, db, directory=str(MIGRATIONS_DIR))
    api.init_app(app)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": settings.cors_origins}},
        supports_credentials=True,
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Idempotency-Key",
            "If-Match",
            "X-Request-ID",
        ],
        expose_headers=[REQUEST_ID_HEADER, "ETag", "Retry-After", "Idempotent-Replayed"],
        max_age=600,
    )
    init_request_context(app)
    init_security_headers(app, hsts=settings.hsts_enabled)
    register_error_handlers(app)  # after api.init_app so ours take precedence

    api.register_blueprint(health_blp)
    register_cli(app)
    load_job_handlers()
    app.extensions[MIGRATIONS_DIR_KEY] = MIGRATIONS_DIR
    return app
