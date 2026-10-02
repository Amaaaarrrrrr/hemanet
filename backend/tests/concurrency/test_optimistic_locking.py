"""ORM version_id_col closes the race between If-Match and UPDATE."""

import pytest
from flask import Flask
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.extensions import db
from tests.support.models import Widget

pytestmark = pytest.mark.concurrency


def test_second_concurrent_update_fails_with_stale_data(real_app: Flask) -> None:
    widget = Widget(name="v1")
    db.session.add(widget)
    db.session.commit()

    first, second = Session(db.engine), Session(db.engine)
    try:
        a = first.get_one(Widget, widget.id)
        b = second.get_one(Widget, widget.id)  # both loaded version 1
        a.name = "from-a"
        first.commit()

        b.name = "from-b"
        with pytest.raises(StaleDataError):
            second.commit()
    finally:
        first.close()
        second.close()

    db.session.expire_all()
    stored = db.session.get_one(Widget, widget.id)
    assert (stored.name, stored.version) == ("from-a", 2)
