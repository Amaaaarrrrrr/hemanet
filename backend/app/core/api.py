"""API conventions shared by every route module.

Use ``app.core.api.Blueprint`` instead of ``flask_smorest.Blueprint``: its
argument parser rejects unknown fields in *every* location (§N.1: "unknown
params → 400"). webargs' default silently drops unknown query parameters.
"""

import flask_smorest
from marshmallow import EXCLUDE, RAISE
from webargs.flaskparser import FlaskParser


class StrictParser(FlaskParser):
    DEFAULT_UNKNOWN_BY_LOCATION = {  # noqa: RUF012 - webargs reads this class attribute
        "json": RAISE,
        "form": RAISE,
        "json_or_form": RAISE,
        "query": RAISE,
        "querystring": RAISE,
        "files": RAISE,
        # Browsers and proxies add arbitrary headers and cookies.
        "headers": EXCLUDE,
        "cookies": EXCLUDE,
    }


class Blueprint(flask_smorest.Blueprint):  # type: ignore[misc]
    ARGUMENTS_PARSER = StrictParser()
