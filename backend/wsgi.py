"""HemaNet API entry point.

PHASE E0 PLACEHOLDER: this module exists only so the container stack can start.
It is replaced by the ``create_app()`` factory in Phase E1.1 (see
docs/blueprint/07-frontend-and-backend-structure.md §P.1). It must not grow
any configuration, database access or domain behaviour.
"""

from flask import Flask


def build_placeholder_app() -> Flask:
    app = Flask("hemanet")

    @app.get("/")
    def index() -> dict[str, str]:
        return {"service": "hemanet-api", "phase": "E0", "status": "placeholder"}

    return app


app = build_placeholder_app()
