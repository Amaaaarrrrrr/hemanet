"""Error envelope and exception mapping (blueprint §N.1 "Error format").

Every error response has the shape::

    {"error": {"code": "...", "message": "...", "details": [...], "request_id": "..."}}

Messages are generic; stack traces and internal details never leave the server.
"""

from collections.abc import Mapping
from typing import Any

import structlog
from flask import Flask, Response, jsonify
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm.exc import StaleDataError
from werkzeug.exceptions import HTTPException

from app.core.request_context import current_request_id

log = structlog.get_logger(__name__)

ErrorDetail = dict[str, str]


class AppError(Exception):
    """Base class for errors that map to a documented API error code."""

    status_code = 500
    code = "INTERNAL_ERROR"
    message = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        details: list[ErrorDetail] | None = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.details = details or []
        super().__init__(self.message)


class ValidationFailed(AppError):
    status_code = 400
    code = "VALIDATION_ERROR"
    message = "The request is invalid."


class MalformedRequest(AppError):
    status_code = 400
    code = "MALFORMED_REQUEST"
    message = "The request could not be parsed."


class NotFound(AppError):
    status_code = 404
    code = "NOT_FOUND"
    message = "The requested resource was not found."


class Conflict(AppError):
    status_code = 409
    code = "CONFLICT"
    message = "The request conflicts with the current state of the resource."


class VersionConflict(Conflict):
    code = "VERSION_CONFLICT"
    message = "The resource was modified by someone else. Reload and try again."


class IdempotencyKeyReused(Conflict):
    code = "IDEMPOTENCY_KEY_REUSED"
    message = "This Idempotency-Key was already used for a different request."


class BusinessRuleViolation(AppError):
    status_code = 422
    code = "BUSINESS_RULE_VIOLATION"
    message = "The request violates a business rule."


class ServiceUnavailable(AppError):
    status_code = 503
    code = "SERVICE_UNAVAILABLE"
    message = "The service is temporarily unavailable. Try again shortly."


# Codes for plain HTTP errors raised by Flask/Werkzeug (routing, body size, …).
# 405/413/415 are additions to the §N.1 table (see docs/backend-foundation.md).
_HTTP_STATUS_CODES: Mapping[int, tuple[str, str]] = {
    400: ("MALFORMED_REQUEST", "The request could not be parsed."),
    401: ("UNAUTHENTICATED", "Authentication is required."),
    403: ("FORBIDDEN", "You do not have permission to perform this action."),
    404: ("NOT_FOUND", "The requested resource was not found."),
    405: ("METHOD_NOT_ALLOWED", "This method is not allowed for this resource."),
    409: ("CONFLICT", "The request conflicts with the current state of the resource."),
    413: ("PAYLOAD_TOO_LARGE", "The request body is too large."),
    415: ("UNSUPPORTED_MEDIA_TYPE", "The request content type is not supported."),
    429: ("RATE_LIMITED", "Too many requests. Try again later."),
    503: ("SERVICE_UNAVAILABLE", "The service is temporarily unavailable. Try again shortly."),
}


def error_response(
    status: int, code: str, message: str, details: list[ErrorDetail] | None = None
) -> Response:
    response = jsonify(
        {
            "error": {
                "code": code,
                "message": message,
                "details": details or [],
                "request_id": current_request_id(),
            }
        }
    )
    response.status_code = status
    return response


def _webargs_details(messages: Any) -> tuple[str, list[ErrorDetail]]:
    """Flatten webargs/marshmallow messages: ``{"json": {"field": ["msg"]}}``."""
    details: list[ErrorDetail] = []

    def walk(prefix: str, value: Any) -> None:
        if isinstance(value, Mapping):
            for key, nested in value.items():
                walk(f"{prefix}.{key}" if prefix else str(key), nested)
        elif isinstance(value, list) and all(isinstance(item, str) for item in value):
            details.extend({"field": prefix, "issue": item} for item in value)
        else:
            details.append({"field": prefix, "issue": str(value)})

    if isinstance(messages, Mapping):
        for location, fields in messages.items():
            # Drop the webargs location prefix ("json", "query") from field names.
            if isinstance(fields, Mapping):
                walk("", fields)
            else:
                walk(str(location), fields)
    unknown = any(d["issue"] == "Unknown field." for d in details)
    return ("UNKNOWN_FIELD" if unknown else "VALIDATION_ERROR"), details


def register_error_handlers(app: Flask) -> None:
    """Register handlers. Must run *after* flask-smorest's ``Api.init_app``."""

    @app.errorhandler(AppError)
    def _app_error(exc: AppError) -> Response:
        return error_response(exc.status_code, exc.code, exc.message, exc.details)

    @app.errorhandler(HTTPException)
    def _http_error(exc: HTTPException) -> Response:
        status = exc.code or 500
        data = getattr(exc, "data", None) or {}
        if status == 422 and "messages" in data:
            # webargs schema validation: §N.1 reserves 422 for business rules.
            code, details = _webargs_details(data["messages"])
            message = (
                "The request contains unknown fields."
                if code == "UNKNOWN_FIELD"
                else "The request is invalid."
            )
            return error_response(400, code, message, details)
        code, message = _HTTP_STATUS_CODES.get(
            status,
            ("INTERNAL_ERROR", "An unexpected error occurred.")
            if status >= 500
            else ("MALFORMED_REQUEST", "The request could not be processed."),
        )
        response = error_response(status, code, message)
        valid_methods = getattr(exc, "valid_methods", None)
        if status == 405 and valid_methods:
            response.headers["Allow"] = ", ".join(valid_methods)
        return response

    @app.errorhandler(StaleDataError)
    def _stale(_exc: StaleDataError) -> Response:
        return error_response(409, VersionConflict.code, VersionConflict.message)

    @app.errorhandler(OperationalError)
    def _db_unavailable(exc: DBAPIError) -> Response:
        log.warning("database unavailable", error_type=type(exc.orig).__name__)
        return error_response(503, ServiceUnavailable.code, ServiceUnavailable.message)

    @app.errorhandler(Exception)
    def _unexpected(exc: Exception) -> Response:
        log.exception("unhandled exception", error_type=type(exc).__name__)
        return error_response(500, AppError.code, AppError.message)
