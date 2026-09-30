"""Smoke tests for the Phase E0 placeholder API (replaced in E1)."""

from wsgi import build_placeholder_app


def test_index_returns_placeholder_payload() -> None:
    client = build_placeholder_app().test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert response.get_json() == {
        "service": "hemanet-api",
        "phase": "E0",
        "status": "placeholder",
    }


def test_unknown_route_returns_404() -> None:
    client = build_placeholder_app().test_client()

    assert client.get("/does-not-exist").status_code == 404
