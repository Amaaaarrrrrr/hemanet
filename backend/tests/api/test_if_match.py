"""Optimistic concurrency with If-Match / version (§N.1)."""

from flask.testing import FlaskClient

from app.core.concurrency import etag_for, parse_if_match

USER = "0192a000-0000-7000-8000-00000000000a"


def create(client: FlaskClient) -> dict[str, object]:
    response = client.post(
        "/_test/widgets",
        json={"name": "original"},
        headers={"Idempotency-Key": "if-match-setup", "X-Test-User": USER},
    )
    body: dict[str, object] = response.get_json()
    return body


def test_update_with_current_version_succeeds_and_bumps_version(client: FlaskClient) -> None:
    widget = create(client)

    response = client.patch(
        f"/_test/widgets/{widget['id']}", json={"name": "renamed"}, headers={"If-Match": '"1"'}
    )

    assert response.status_code == 200
    assert response.get_json()["version"] == 2
    assert response.headers["ETag"] == '"2"'


def test_stale_version_is_409_version_conflict(client: FlaskClient) -> None:
    widget = create(client)
    client.patch(f"/_test/widgets/{widget['id']}", json={"name": "b"}, headers={"If-Match": '"1"'})

    response = client.patch(
        f"/_test/widgets/{widget['id']}", json={"name": "c"}, headers={"If-Match": '"1"'}
    )

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "VERSION_CONFLICT"


def test_missing_or_invalid_if_match_is_400(client: FlaskClient) -> None:
    widget = create(client)
    url = f"/_test/widgets/{widget['id']}"

    missing = client.patch(url, json={"name": "b"})
    invalid = client.patch(url, json={"name": "b"}, headers={"If-Match": "abc"})

    assert missing.status_code == invalid.status_code == 400
    assert missing.get_json()["error"]["details"] == [{"field": "If-Match", "issue": "required"}]
    assert invalid.get_json()["error"]["details"] == [{"field": "If-Match", "issue": "invalid"}]


def test_etag_formats() -> None:
    assert etag_for(3) == '"3"'
    assert parse_if_match('"3"') == parse_if_match("3") == parse_if_match('W/"3"') == 3
    assert parse_if_match('"x"') is None
