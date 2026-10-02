import uuid

from flask.testing import FlaskClient


def test_request_id_is_generated_as_uuid7(client: FlaskClient) -> None:
    response = client.get("/healthz")

    assert uuid.UUID(response.headers["X-Request-ID"]).version == 7


def test_valid_client_request_id_is_echoed(client: FlaskClient) -> None:
    response = client.get("/healthz", headers={"X-Request-ID": "client-trace-1234"})

    assert response.headers["X-Request-ID"] == "client-trace-1234"


def test_unsafe_client_request_id_is_replaced(client: FlaskClient) -> None:
    unsafe = "<script>alert(1)</script>"
    response = client.get("/healthz", headers={"X-Request-ID": unsafe})

    assert response.headers["X-Request-ID"] != unsafe
    assert uuid.UUID(response.headers["X-Request-ID"]).version == 7


def test_request_log_has_path_but_not_query_string(client: FlaskClient, capsys) -> None:  # type: ignore[no-untyped-def]
    client.get("/healthz?phone=0712345678")

    logs = capsys.readouterr().out
    assert "request completed" in logs and "/healthz" in logs
    assert "0712345678" not in logs
