"""Log redaction: no personal data or secrets reach the logs (NFR-O1)."""

import json
import logging

import pytest
import structlog

from app.core.logging import REDACTED, configure_logging, redact_text, redact_value


@pytest.mark.parametrize(
    "text",
    [
        "contact jane.doe@example.com now",
        "call +254712345678",
        "call 254712345678",
        "call 0712345678",
        "call 0712 345 678",
        "Authorization: Bearer abc.def-ghi",
        "token eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.c2lnbmF0dXJl",
    ],
)
def test_sensitive_patterns_are_scrubbed(text: str) -> None:
    redacted = redact_text(text)

    assert REDACTED in redacted
    for secret in ("jane.doe", "712345678", "712 345 678", "abc.def", "eyJhbGci"):
        assert secret not in redacted


def test_dsn_password_is_scrubbed() -> None:
    redacted = redact_text("postgresql+psycopg://hemanet:s3cret@db:5432/hemanet")

    assert "s3cret" not in redacted
    assert redacted.startswith("postgresql+psycopg://")


@pytest.mark.parametrize(
    "text", ["2026-10-02T13:31:06Z", "job 42 took 15 ms", "status 503", "v1.2.3"]
)
def test_ordinary_values_are_kept(text: str) -> None:
    assert redact_text(text) == text


def test_sensitive_keys_are_redacted_recursively() -> None:
    value = redact_value(
        {"user": {"Email": "a@b.co", "phone-number": "1", "count": 3}, "items": [{"notes": "x"}]}
    )

    assert value == {
        "user": {"Email": REDACTED, "phone-number": REDACTED, "count": 3},
        "items": [{"notes": REDACTED}],
    }


def test_json_logs_are_redacted_end_to_end(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO", "json")
    log = structlog.get_logger("test")

    log.info(
        "donor contacted via jane@example.com",
        email="jane@example.com",
        phone="+254712345678",
        notes="free text",
        password="hunter2",
        count=3,
    )
    try:
        raise ValueError("failed for +254700000001")
    except ValueError:
        log.exception("handler failed")
    logging.getLogger("thirdparty").warning("token=Bearer secrettoken")

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    first, second, third = lines
    assert first["event"] == f"donor contacted via {REDACTED}"
    assert first["email"] == first["phone"] == first["notes"] == first["password"] == REDACTED
    assert first["count"] == 3
    assert first["level"] == "info" and "timestamp" in first
    assert "+254700000001" not in second["exception"] and REDACTED in second["exception"]
    assert "secrettoken" not in third["event"]
