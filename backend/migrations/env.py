"""Alembic environment, driven by Flask-Migrate and the application's metadata."""

import logging
from typing import Any

from alembic import context
from flask import current_app

config = context.config
logger = logging.getLogger("alembic.env")

target_db = current_app.extensions["migrate"].db


def get_metadata() -> Any:
    return target_db.metadatas[None]


def run_migrations_offline() -> None:
    context.configure(
        url=target_db.engine.url.render_as_string(hide_password=False),
        target_metadata=get_metadata(),
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    def process_revision_directives(_context: Any, _revision: Any, directives: list[Any]) -> None:
        # Never create an empty migration from `flask db migrate`.
        if getattr(config.cmd_opts, "autogenerate", False) and directives[0].upgrade_ops.is_empty():
            directives[:] = []
            logger.info("No changes in schema detected.")

    conf_args = dict(current_app.extensions["migrate"].configure_args)
    conf_args.setdefault("process_revision_directives", process_revision_directives)
    conf_args.setdefault("compare_type", True)
    conf_args.setdefault("compare_server_default", True)

    with target_db.engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=get_metadata(),
            **conf_args,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
