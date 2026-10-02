from flask.testing import FlaskClient

from app import create_app
from app.core.clock import FrozenClock
from tests.api.test_security_headers import STAGING
from tests.conftest import START, make_settings


def test_openapi_document_is_published_outside_production(client: FlaskClient) -> None:
    response = client.get("/api/v1/openapi.json")

    assert response.status_code == 200
    spec = response.get_json()
    assert spec["openapi"].startswith("3.1")
    assert spec["info"]["title"] == "HemaNet API"
    assert {"/healthz", "/readyz"} <= set(spec["paths"])


def test_openapi_document_is_hidden_in_production() -> None:
    settings = make_settings(**(STAGING | {"app_env": "production"}))
    app = create_app(settings, clock=FrozenClock(START))

    assert app.test_client().get("/api/v1/openapi.json").status_code == 404
