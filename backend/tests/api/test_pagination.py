"""Cursor pagination through a list endpoint (§N.1)."""

from datetime import timedelta

from flask.testing import FlaskClient

from app.core.clock import FrozenClock
from app.extensions import db
from tests.support.models import Widget


def seed(clock: FrozenClock, count: int) -> list[str]:
    names = []
    for i in range(count):
        db.session.add(Widget(name=f"w{i}"))
        db.session.flush()
        names.append(f"w{i}")
        clock.advance(timedelta(seconds=1))
    return names


def collect(client: FlaskClient, query: str) -> tuple[list[str], int]:
    names: list[str] = []
    pages = 0
    cursor = None
    while True:
        url = f"/_test/widgets?{query}" + (f"&cursor={cursor}" if cursor else "")
        body = client.get(url).get_json()
        pages += 1
        names += [item["name"] for item in body["data"]]
        cursor = body["page"]["next_cursor"]
        if cursor is None:
            return names, pages


def test_pages_through_all_items_in_order(client: FlaskClient, clock: FrozenClock) -> None:
    expected = seed(clock, 5)

    names, pages = collect(client, "limit=2")

    assert names == expected
    assert pages == 3


def test_descending_order(client: FlaskClient, clock: FrozenClock) -> None:
    expected = seed(clock, 5)

    names, _ = collect(client, "limit=2&order=desc")

    assert names == list(reversed(expected))


def test_default_limit_and_envelope(client: FlaskClient, clock: FrozenClock) -> None:
    seed(clock, 3)

    body = client.get("/_test/widgets").get_json()

    assert set(body) == {"data", "page"}
    assert body["page"] == {"next_cursor": None, "limit": 25}


def test_limit_bounds_and_unknown_params(client: FlaskClient) -> None:
    too_big = client.get("/_test/widgets?limit=101")
    zero = client.get("/_test/widgets?limit=0")
    unknown = client.get("/_test/widgets?sort=-name")

    assert too_big.status_code == zero.status_code == unknown.status_code == 400
    assert too_big.get_json()["error"]["code"] == "VALIDATION_ERROR"
    assert unknown.get_json()["error"]["code"] == "UNKNOWN_FIELD"


def test_invalid_cursor_is_400(client: FlaskClient) -> None:
    response = client.get("/_test/widgets?cursor=garbage")

    assert response.status_code == 400
    assert response.get_json()["error"]["details"] == [{"field": "cursor", "issue": "invalid"}]
