import pytest

from app.config import ConfigurationError, load_settings

DEV_URL = "postgresql+psycopg://u:change-me-local@localhost:5432/hemanet"
PROD_URL = "postgresql+psycopg://u:Xk9-real-secret@db.internal:5432/hemanet"


def test_local_defaults() -> None:
    settings = load_settings(app_env="local", database_url=DEV_URL, cors_allowed_origins="")

    assert settings.is_development
    assert settings.cors_origins == []
    assert settings.expose_openapi
    assert not settings.hsts_enabled


def test_cors_origins_are_parsed_from_a_comma_separated_list() -> None:
    settings = load_settings(
        database_url=DEV_URL, cors_allowed_origins=" http://localhost:5173 ,http://127.0.0.1:5173,"
    )

    assert settings.cors_origins == ["http://localhost:5173", "http://127.0.0.1:5173"]


def test_production_is_strict_and_hides_openapi() -> None:
    settings = load_settings(
        app_env="production",
        database_url=PROD_URL,
        cors_allowed_origins="https://app.hemanet.example",
        log_format="json",
    )

    assert not settings.expose_openapi
    assert settings.hsts_enabled


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"cors_allowed_origins": "*"}, "CORS"),
        ({"cors_allowed_origins": "http://app.example"}, "CORS"),
        ({"database_url": "postgresql+psycopg://u:change-me-x@db/h"}, "placeholder"),
        ({"log_format": "console"}, "LOG_FORMAT"),
    ],
)
def test_non_development_rejects_unsafe_settings(overrides: dict[str, str], message: str) -> None:
    values = {
        "app_env": "staging",
        "database_url": PROD_URL,
        "cors_allowed_origins": "https://app.example",
        "log_format": "json",
    } | overrides

    with pytest.raises(ConfigurationError, match=message):
        load_settings(**values)


def test_errors_never_echo_the_database_password() -> None:
    with pytest.raises(ConfigurationError) as excinfo:
        load_settings(app_env="staging", database_url="postgresql+psycopg://u:change-me-SECRET@h/d")

    assert "SECRET" not in str(excinfo.value)


def test_database_url_scheme_is_enforced() -> None:
    with pytest.raises(ConfigurationError, match="postgresql\\+psycopg"):
        load_settings(database_url="sqlite:///hemanet.db")


def test_heartbeat_must_be_shorter_than_readiness_window() -> None:
    with pytest.raises(ConfigurationError, match="WORKER_HEARTBEAT_SECONDS"):
        load_settings(
            database_url=DEV_URL,
            worker_heartbeat_seconds=120,
            readiness_heartbeat_max_age_seconds=60,
        )


def test_database_url_is_secret_in_repr() -> None:
    settings = load_settings(database_url=DEV_URL)

    assert "change-me-local" not in repr(settings)
