"""Idempotency-Key behaviour (§N.1) through a test route that creates widgets."""

from datetime import timedelta

from flask.testing import FlaskClient
from sqlalchemy import func, select

from app.core.clock import FrozenClock
from app.core.idempotency import IdempotencyKey, purge_expired
from app.extensions import db
from tests.support.models import Widget

USER_A = "0192a000-0000-7000-8000-00000000000a"
USER_B = "0192a000-0000-7000-8000-00000000000b"


def post(client: FlaskClient, body: dict[str, object], key: str | None, user: str = USER_A):  # type: ignore[no-untyped-def]
    headers = {"X-Test-User": user}
    if key is not None:
        headers["Idempotency-Key"] = key
    return client.post("/_test/widgets", json=body, headers=headers)


def widget_count() -> int:
    return db.session.scalar(select(func.count()).select_from(Widget)) or 0


def test_key_is_required(client: FlaskClient) -> None:
    response = post(client, {"name": "a"}, key=None)

    assert response.status_code == 400
    assert response.get_json()["error"]["details"] == [
        {"field": "Idempotency-Key", "issue": "required"}
    ]


def test_key_must_be_well_formed(client: FlaskClient) -> None:
    response = post(client, {"name": "a"}, key="short")

    assert response.status_code == 400
    assert response.get_json()["error"]["details"][0]["issue"] == "invalid"


def test_replay_returns_original_response_without_repeating_work(client: FlaskClient) -> None:
    first = post(client, {"name": "a"}, key="key-replay-0001")
    second = post(client, {"name": "a"}, key="key-replay-0001")

    assert first.status_code == second.status_code == 201
    assert second.get_json() == first.get_json()
    assert second.headers["Idempotent-Replayed"] == "true"
    assert "Idempotent-Replayed" not in first.headers
    assert widget_count() == 1


def test_same_key_with_different_body_is_rejected(client: FlaskClient) -> None:
    post(client, {"name": "a"}, key="key-reuse-00001")

    response = post(client, {"name": "b"}, key="key-reuse-00001")

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"
    assert widget_count() == 1


def test_keys_are_scoped_per_principal(client: FlaskClient) -> None:
    post(client, {"name": "a"}, key="key-shared-0001", user=USER_A)
    response = post(client, {"name": "a"}, key="key-shared-0001", user=USER_B)

    assert response.status_code == 201
    assert "Idempotent-Replayed" not in response.headers
    assert widget_count() == 2


def test_failed_request_releases_the_key(client: FlaskClient) -> None:
    failed = post(client, {"name": "a", "fail": True}, key="failing-request")

    assert failed.status_code == 422
    assert db.session.scalar(select(func.count()).select_from(IdempotencyKey)) == 0


def test_expired_key_is_treated_as_new(client: FlaskClient, clock: FrozenClock) -> None:
    post(client, {"name": "a"}, key="key-expiry-0001")
    clock.advance(timedelta(hours=24, seconds=1))

    response = post(client, {"name": "a"}, key="key-expiry-0001")

    assert response.status_code == 201
    assert "Idempotent-Replayed" not in response.headers
    assert widget_count() == 2


def test_purge_removes_only_expired_keys(client: FlaskClient, clock: FrozenClock) -> None:
    post(client, {"name": "a"}, key="key-purge-00001")
    clock.advance(timedelta(hours=23))
    post(client, {"name": "b"}, key="key-purge-00002")
    clock.advance(timedelta(hours=2))

    removed = purge_expired(db.session, clock.now())

    assert removed == 1
    assert db.session.scalars(select(IdempotencyKey.key)).all() == ["key-purge-00002"]
