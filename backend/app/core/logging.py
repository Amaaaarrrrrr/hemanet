"""Structured JSON logging with redaction (blueprint §U, NFR-O1).

All logs (structlog and stdlib, e.g. gunicorn/SQLAlchemy) go through the same
pipeline. The redaction step runs last before rendering and:

* replaces values of sensitive keys (names, phone numbers, emails, notes,
  tokens, passwords, …) with ``[REDACTED]``, recursively;
* scrubs email addresses, phone numbers, bearer tokens and JWTs from any
  remaining string, including exception text.
"""

import logging
import re
import sys
from collections.abc import Mapping, MutableMapping
from typing import Any, Literal

import structlog
from structlog.typing import EventDict, Processor, WrappedLogger

REDACTED = "[REDACTED]"

SENSITIVE_KEYS = frozenset(
    {
        "password",
        "new_password",
        "current_password",
        "password_hash",
        "token",
        "access_token",
        "refresh_token",
        "id_token",
        "authorization",
        "cookie",
        "set_cookie",
        "secret",
        "api_key",
        "otp",
        "otp_code",
        "totp",
        "totp_secret",
        "recovery_code",
        "email",
        "phone",
        "phone_number",
        "msisdn",
        "name",
        "first_name",
        "last_name",
        "full_name",
        "display_name",
        "national_id",
        "date_of_birth",
        "dob",
        "address",
        "notes",
        "note",
        "free_text",
        "database_url",
    }
)

_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),  # JWT
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),  # email
    # Phone numbers: +254712345678, 254712345678, 0712345678, 0712 345 678, 712-345-678.
    re.compile(r"(?<![\w:.-])(?:\+?\d{1,3}[ -]?)?\d{3}[ -]?\d{3}[ -]?\d{3,4}(?![\w:.-])"),
    re.compile(r"(?i)\b(postgres(?:ql)?(?:\+\w+)?://)[^\s@/]+@"),  # DSN credentials
)


def redact_text(text: str) -> str:
    for pattern in _PATTERNS:
        if pattern.groups:
            text = pattern.sub(lambda m: f"{m.group(1)}{REDACTED}@", text)
        else:
            text = pattern.sub(REDACTED, text)
    return text


def _normalise_key(key: object) -> str:
    return str(key).lower().replace("-", "_")


def redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, Mapping):
        return {
            k: REDACTED if _normalise_key(k) in SENSITIVE_KEYS else redact_value(v)
            for k, v in value.items()
        }
    if isinstance(value, list | tuple | set):
        return [redact_value(v) for v in value]
    return value


# Keys produced by the logging pipeline itself; never personal data.
_PIPELINE_KEYS = frozenset({"timestamp", "level", "logger", "request_id"})


def redaction_processor(
    _logger: WrappedLogger, _method_name: str, event_dict: EventDict
) -> EventDict:
    for key in list(event_dict):
        if key in _PIPELINE_KEYS:
            continue
        if _normalise_key(key) in SENSITIVE_KEYS:
            event_dict[key] = REDACTED
        else:
            event_dict[key] = redact_value(event_dict[key])
    return event_dict


def _drop_color_message(
    _logger: WrappedLogger, _method_name: str, event_dict: EventDict
) -> EventDict:
    event_dict.pop("color_message", None)
    return event_dict


def build_processors(
    fmt: Literal["json", "console"],
) -> tuple[list[Processor], list[Processor]]:
    """Return (shared pre-chain, final formatter chain). Exposed for tests."""
    shared: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _drop_color_message,
    ]
    renderer: Processor = (
        structlog.processors.JSONRenderer()
        if fmt == "json"
        else structlog.dev.ConsoleRenderer(colors=False)
    )
    final: list[Processor] = [
        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
        structlog.processors.format_exc_info,
        redaction_processor,
        renderer,
    ]
    return shared, final


class _StdoutHandler(logging.StreamHandler):  # type: ignore[type-arg]
    """Writes to whatever ``sys.stdout`` is at emit time (robust to stream swapping)."""

    def __init__(self) -> None:
        super().__init__(sys.stdout)

    @property
    def stream(self) -> Any:
        return sys.stdout

    @stream.setter
    def stream(self, _value: Any) -> None:
        pass


def configure_logging(level: str = "INFO", fmt: Literal["json", "console"] = "json") -> None:
    shared, final = build_processors(fmt)
    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )
    handler = _StdoutHandler()
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(foreign_pre_chain=shared, processors=final)
    )
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
    # SQL statements may contain personal data in bound parameters: never log them.
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)


def redact_mapping(data: MutableMapping[str, Any]) -> dict[str, Any]:
    """Redact a plain mapping (e.g. before storing an error in the database)."""
    result: dict[str, Any] = redact_value(dict(data))
    return result
