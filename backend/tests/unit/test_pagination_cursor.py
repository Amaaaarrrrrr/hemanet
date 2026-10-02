import uuid
from datetime import UTC, datetime

import pytest

from app.core.errors import ValidationFailed
from app.core.pagination import decode_cursor, encode_cursor


def test_round_trip_preserves_types() -> None:
    values = [datetime(2026, 10, 2, 9, 30, tzinfo=UTC), uuid.uuid4(), 42, "abc"]

    assert decode_cursor(encode_cursor(values), 4) == values


@pytest.mark.parametrize(
    "cursor",
    [
        "not-base64!!",
        encode_cursor([1])[:-2] + "zz",
        "eyJ2IjogOSwgImsiOiBbXX0",  # {"v": 9, "k": []}: unknown version
    ],
)
def test_tampered_cursors_are_rejected(cursor: str) -> None:
    with pytest.raises(ValidationFailed) as excinfo:
        decode_cursor(cursor, 1)

    assert excinfo.value.details == [{"field": "cursor", "issue": "invalid"}]


def test_cursor_shape_must_match_the_sort_keys() -> None:
    with pytest.raises(ValidationFailed):
        decode_cursor(encode_cursor([1, 2]), 1)


def test_unsupported_values_cannot_be_encoded() -> None:
    with pytest.raises(TypeError):
        encode_cursor([True])
