"""Request IDs and request logging (blueprint §N.1 "Tracing", NFR-O1).

Every response carries ``X-Request-ID``. A client-supplied value is echoed only
if it is a safe token; otherwise a new UUIDv7 is generated.
"""

import re
import time

import structlog
from flask import Flask, Response, g, has_request_context, request

from app.core.ids import new_id

REQUEST_ID_HEADER = "X-Request-ID"
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{8,128}$")

log = structlog.get_logger("hemanet.request")


def current_request_id() -> str | None:
    if not has_request_context():
        return None
    request_id: str | None = g.get("request_id")
    return request_id


def init_request_context(app: Flask) -> None:
    @app.before_request
    def _start() -> None:
        supplied = request.headers.get(REQUEST_ID_HEADER, "")
        g.request_id = supplied if _VALID_REQUEST_ID.fullmatch(supplied) else str(new_id())
        g.request_started = time.perf_counter()
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=g.request_id)

    @app.after_request
    def _finish(response: Response) -> Response:
        request_id = current_request_id()
        if request_id:
            response.headers[REQUEST_ID_HEADER] = request_id
        started = g.get("request_started")
        # Path only: query strings may carry personal data and are never logged.
        log.info(
            "request completed",
            method=request.method,
            path=request.path,
            status=response.status_code,
            duration_ms=round((time.perf_counter() - started) * 1000, 1) if started else None,
        )
        return response

    @app.teardown_request
    def _clear(_exc: BaseException | None) -> None:
        structlog.contextvars.clear_contextvars()
