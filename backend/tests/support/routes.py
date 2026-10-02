"""Test-only API routes that exercise the E1a infrastructure end to end."""

import uuid
from typing import Any

from flask import Response, jsonify, request
from marshmallow import Schema, fields, validate
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm.exc import StaleDataError

from app.core.api import Blueprint
from app.core.concurrency import etag_for, require_if_match
from app.core.errors import BusinessRuleViolation, NotFound
from app.core.idempotency import idempotent
from app.core.pagination import PageArgsSchema, paginate
from app.extensions import db
from tests.support.models import Widget

blp = Blueprint("test_support", __name__, url_prefix="/_test")


class WidgetIn(Schema):
    name = fields.String(required=True, validate=validate.Length(min=1, max=100))
    fail = fields.Boolean(load_default=False)


class WidgetPatch(Schema):
    name = fields.String(required=True, validate=validate.Length(min=1, max=100))


class WidgetListArgs(PageArgsSchema):
    order = fields.String(load_default="asc", validate=validate.OneOf(["asc", "desc"]))


def test_principal() -> uuid.UUID:
    return uuid.UUID(request.headers["X-Test-User"])


test_principal.__test__ = False  # type: ignore[attr-defined]


def serialize(widget: Widget) -> dict[str, Any]:
    return {"id": str(widget.id), "name": widget.name, "version": widget.version}


@blp.route("/widgets", methods=["POST"])
@blp.arguments(WidgetIn)
@idempotent(principal=test_principal)
def create_widget(data: dict[str, Any]) -> tuple[dict[str, Any], int]:
    if data["fail"]:
        raise BusinessRuleViolation("Widgets cannot fail.", code="WIDGET_FAILED")
    widget = Widget(name=data["name"])
    db.session.add(widget)
    db.session.flush()
    return serialize(widget), 201


@blp.route("/widgets", methods=["GET"])
@blp.arguments(WidgetListArgs, location="query")
def list_widgets(args: dict[str, Any]) -> dict[str, Any]:
    page = paginate(
        db.session,
        select(Widget),
        order_by=[Widget.created_at, Widget.id],
        limit=args["limit"],
        cursor=args["cursor"],
        descending=args["order"] == "desc",
    )
    return page.envelope(serialize)


@blp.route("/widgets/<uuid:widget_id>", methods=["PATCH"])
@blp.arguments(WidgetPatch)
def update_widget(data: dict[str, Any], widget_id: uuid.UUID) -> Response:
    widget = db.session.get(Widget, widget_id)
    if widget is None:
        raise NotFound()
    require_if_match(widget.version)
    widget.name = data["name"]
    db.session.flush()
    response = jsonify(serialize(widget))
    response.headers["ETag"] = etag_for(widget.version)
    return response


@blp.route("/echo", methods=["POST"])
@blp.arguments(WidgetIn)
def echo(data: dict[str, Any]) -> dict[str, Any]:
    return data


@blp.route("/boom")
def boom() -> None:
    raise RuntimeError("internal detail: contact jane.doe@example.com at +254712345678")


@blp.route("/db-down")
def db_down() -> None:
    raise OperationalError("SELECT 1", {}, ConnectionRefusedError("connection refused"))


@blp.route("/stale")
def stale() -> None:
    raise StaleDataError("UPDATE matched 0 rows")
