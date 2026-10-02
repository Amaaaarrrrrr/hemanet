from flask.testing import FlaskClient

from app import create_app
from app.core.clock import FrozenClock
from tests.conftest import START, make_settings

STAGING = {
    "app_env": "staging",
    "database_url": "postgresql+psycopg://hemanet:Real-Secret-1@127.0.0.1:1/hemanet_test",
    "cors_allowed_origins": "https://app.hemanet.example",
    "log_format": "json",
}


def test_security_headers_on_every_response(client: FlaskClient) -> None:
    for response in (client.get("/healthz"), client.get("/missing")):
        headers = response.headers
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-Frame-Options"] == "DENY"
        assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "default-src 'none'" in headers["Content-Security-Policy"]
        assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
        assert "unsafe-inline" not in headers["Content-Security-Policy"]
        assert headers["Cache-Control"] == "no-store"
        assert "Strict-Transport-Security" not in headers  # local/ci are not served over TLS


def test_hsts_outside_development() -> None:
    app = create_app(make_settings(**STAGING), clock=FrozenClock(START))

    response = app.test_client().get("/healthz")

    assert response.headers["Strict-Transport-Security"].startswith("max-age=31536000")
