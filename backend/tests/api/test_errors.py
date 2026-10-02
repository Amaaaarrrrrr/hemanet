"""Error envelope (§N.1): codes, statuses and no internal details."""

import pytest
from flask.testing import FlaskClient


def assert_envelope(body: dict[str, object], code: str) -> dict[str, object]:
    error = body["error"]
    assert isinstance(error, dict)
    assert set(error) == {"code", "message", "details", "request_id"}
    assert error["code"] == code
    assert error["request_id"]
    return error


def test_unknown_route_is_404_not_found(client: FlaskClient) -> None:
    response = client.get("/does-not-exist")

    assert response.status_code == 404
    error = assert_envelope(response.get_json(), "NOT_FOUND")
    assert error["request_id"] == response.headers["X-Request-ID"]


def test_wrong_method_is_405_with_allow_header(client: FlaskClient) -> None:
    response = client.delete("/healthz")

    assert response.status_code == 405
    assert_envelope(response.get_json(), "METHOD_NOT_ALLOWED")
    assert "GET" in response.headers["Allow"]


def test_malformed_json_is_400(client: FlaskClient) -> None:
    response = client.post(
        "/_test/echo", data="{not json", headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 400
    assert_envelope(response.get_json(), "MALFORMED_REQUEST")


def test_unknown_json_field_is_400_unknown_field(client: FlaskClient) -> None:
    response = client.post("/_test/echo", json={"name": "x", "status": "COMPLETED"})

    assert response.status_code == 400
    error = assert_envelope(response.get_json(), "UNKNOWN_FIELD")
    assert {"field": "status", "issue": "Unknown field."} in error["details"]  # type: ignore[operator]


def test_schema_validation_is_400_validation_error_not_422(client: FlaskClient) -> None:
    response = client.post("/_test/echo", json={"name": ""})

    assert response.status_code == 400
    error = assert_envelope(response.get_json(), "VALIDATION_ERROR")
    assert error["details"][0]["field"] == "name"  # type: ignore[index]


def test_oversized_body_is_413(client: FlaskClient) -> None:
    response = client.post(
        "/_test/echo", data=b"x" * (1_048_576 + 1), headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 413
    assert_envelope(response.get_json(), "PAYLOAD_TOO_LARGE")


def test_business_rule_violation_is_422(client: FlaskClient) -> None:
    response = client.post(
        "/_test/widgets",
        json={"name": "w", "fail": True},
        headers={
            "Idempotency-Key": "key-business-rule",
            "X-Test-User": "0192a000-0000-7000-8000-000000000001",
        },
    )

    assert response.status_code == 422
    assert_envelope(response.get_json(), "WIDGET_FAILED")


def test_unexpected_exception_is_generic_500(
    client: FlaskClient, capsys: pytest.CaptureFixture[str]
) -> None:
    response = client.get("/_test/boom")

    assert response.status_code == 500
    error = assert_envelope(response.get_json(), "INTERNAL_ERROR")
    assert error["message"] == "An unexpected error occurred."
    assert b"Traceback" not in response.data and b"jane.doe" not in response.data
    logs = capsys.readouterr().out
    assert "RuntimeError" in logs  # logged server side…
    assert "jane.doe@example.com" not in logs and "+254712345678" not in logs  # …redacted


def test_database_outage_is_503(client: FlaskClient) -> None:
    response = client.get("/_test/db-down")

    assert response.status_code == 503
    assert_envelope(response.get_json(), "SERVICE_UNAVAILABLE")


def test_stale_orm_update_is_409_version_conflict(client: FlaskClient) -> None:
    response = client.get("/_test/stale")

    assert response.status_code == 409
    assert_envelope(response.get_json(), "VERSION_CONFLICT")
