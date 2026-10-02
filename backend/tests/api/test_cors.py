from flask.testing import FlaskClient

PREFLIGHT = {
    "Access-Control-Request-Method": "POST",
    "Access-Control-Request-Headers": "Content-Type, Idempotency-Key",
}


def test_allowed_origin_gets_cors_headers(client: FlaskClient) -> None:
    response = client.options(
        "/api/v1/openapi.json", headers={"Origin": "http://localhost:5173", **PREFLIGHT}
    )

    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"
    assert response.headers["Access-Control-Allow-Credentials"] == "true"
    assert "idempotency-key" in response.headers["Access-Control-Allow-Headers"].lower()


def test_other_origins_are_not_allowed(client: FlaskClient) -> None:
    response = client.get("/api/v1/openapi.json", headers={"Origin": "https://evil.example"})

    assert "Access-Control-Allow-Origin" not in response.headers


def test_no_wildcard_origin(client: FlaskClient) -> None:
    response = client.get("/api/v1/openapi.json", headers={"Origin": "http://localhost:5173"})

    assert response.headers["Access-Control-Allow-Origin"] != "*"
