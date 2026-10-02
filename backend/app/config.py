"""Typed settings from environment variables (blueprint §P.1 ``config.py``).

Outside ``local``/``ci`` the settings are strict: no wildcard or non-HTTPS CORS
origins, no placeholder credentials, JSON logs only. Validation errors never
echo input values (the database URL contains a password).
"""

from typing import Literal, Self

from flask import current_app
from pydantic import Field, SecretStr, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AppEnv = Literal["local", "ci", "staging", "pilot", "production"]
SETTINGS_EXTENSION_KEY = "hemanet.settings"
_PLACEHOLDER_MARKERS = ("change-me", "changeme", "placeholder")


class ConfigurationError(RuntimeError):
    pass


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", frozen=True)

    app_env: AppEnv = "local"
    database_url: SecretStr
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["json", "console"] = "json"
    cors_allowed_origins: str = ""
    max_content_length_bytes: int = Field(default=1_048_576, ge=1024, le=50 * 1_048_576)
    db_pool_size: int = Field(default=5, ge=1, le=50)
    idempotency_ttl_hours: int = Field(default=24, ge=1, le=168)
    worker_poll_seconds: float = Field(default=1.0, gt=0, le=60)
    worker_heartbeat_seconds: float = Field(default=30.0, gt=0, le=300)
    readiness_heartbeat_max_age_seconds: float = Field(default=120.0, gt=0, le=3600)
    job_lock_seconds: int = Field(default=300, ge=10, le=86_400)

    @property
    def is_development(self) -> bool:
        return self.app_env in ("local", "ci")

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def expose_openapi(self) -> bool:
        return self.app_env not in ("pilot", "production")

    @property
    def hsts_enabled(self) -> bool:
        return not self.is_development

    @model_validator(mode="after")
    def _check(self) -> Self:
        url = self.database_url.get_secret_value()
        if not url.startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL must use the postgresql+psycopg:// scheme")
        if self.worker_heartbeat_seconds >= self.readiness_heartbeat_max_age_seconds:
            raise ValueError(
                "WORKER_HEARTBEAT_SECONDS must be below READINESS_HEARTBEAT_MAX_AGE_SECONDS"
            )
        if not self.is_development:
            if any(marker in url.lower() for marker in _PLACEHOLDER_MARKERS):
                raise ValueError("DATABASE_URL contains a placeholder credential")
            for origin in self.cors_origins:
                if origin == "*" or not origin.startswith("https://"):
                    raise ValueError("CORS origins must be explicit https:// origins")
            if self.log_format != "json":
                raise ValueError("LOG_FORMAT must be json outside local/ci")
        return self


def load_settings(**overrides: object) -> Settings:
    try:
        return Settings(**overrides)  # type: ignore[arg-type]
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in err['loc']) or 'settings'}: {err['msg']}"
            for err in exc.errors(include_input=False, include_url=False)
        )
        raise ConfigurationError(f"invalid configuration: {problems}") from None


def get_settings() -> Settings:
    settings: Settings = current_app.extensions[SETTINGS_EXTENSION_KEY]
    return settings
