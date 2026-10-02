"""Optimistic concurrency via ``If-Match`` (blueprint §N.1 "Concurrency").

Mutable resources expose ``version`` (and an ``ETag`` of ``"<version>"``).
Updates must send ``If-Match: "<version>"``; a stale version gives 409
``VERSION_CONFLICT``. The ORM ``version_id_col`` (``VersionMixin``) closes the
race between this check and the UPDATE.
"""

import re

from flask import request

from app.core.errors import ValidationFailed, VersionConflict

IF_MATCH_HEADER = "If-Match"
_VERSION_TAG = re.compile(r'^(?:W/)?"?(\d{1,10})"?$')


def etag_for(version: int) -> str:
    return f'"{version}"'


def parse_if_match(value: str | None) -> int | None:
    if value is None:
        return None
    match = _VERSION_TAG.fullmatch(value.strip())
    return int(match.group(1)) if match else None


def require_if_match(current_version: int) -> None:
    raw = request.headers.get(IF_MATCH_HEADER)
    if raw is None:
        raise ValidationFailed(
            "This update requires an If-Match header with the resource version.",
            details=[{"field": IF_MATCH_HEADER, "issue": "required"}],
        )
    expected = parse_if_match(raw)
    if expected is None:
        raise ValidationFailed(
            "The If-Match header is invalid.",
            details=[{"field": IF_MATCH_HEADER, "issue": "invalid"}],
        )
    if expected != current_version:
        raise VersionConflict()
