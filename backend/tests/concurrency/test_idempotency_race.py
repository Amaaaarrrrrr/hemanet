"""Concurrent duplicate submissions with the same Idempotency-Key."""

import threading
from typing import Any

import pytest
from flask import Flask
from sqlalchemy import func, select

from app.extensions import db
from tests.support.models import Widget

pytestmark = pytest.mark.concurrency
HEADERS = {
    "Idempotency-Key": "key-race-000001",
    "X-Test-User": "0192a000-0000-7000-8000-00000000000a",
}


def test_simultaneous_duplicates_create_one_resource(real_app: Flask) -> None:
    results: list[Any] = [None] * 6
    barrier = threading.Barrier(6)

    def submit(slot: int) -> None:
        with real_app.app_context():
            client = real_app.test_client()
            barrier.wait()
            response = client.post("/_test/widgets", json={"name": "same"}, headers=HEADERS)
            results[slot] = (response.status_code, response.get_json())
            db.session.remove()

    threads = [threading.Thread(target=submit, args=(i,)) for i in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert all(status == 201 for status, _ in results)
    assert len({body["id"] for _, body in results}) == 1
    assert db.session.scalar(select(func.count()).select_from(Widget)) == 1
