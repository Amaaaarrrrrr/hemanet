"""``flask jobs …`` commands for operators and manual verification."""

import click
from flask import Flask
from sqlalchemy import func, select

from app.core.clock import utcnow
from app.extensions import db
from app.jobs.builtin import NOOP_JOB_TYPE
from app.jobs.models import Job
from app.jobs.queue import enqueue


def register_cli(app: Flask) -> None:
    @app.cli.group("jobs")
    def jobs() -> None:
        """Background job queue commands."""

    @jobs.command("enqueue-noop")
    def enqueue_noop() -> None:
        """Queue a no-op job (verifies the worker end to end)."""
        job_id = enqueue(db.session, NOOP_JOB_TYPE, now=utcnow())
        db.session.commit()
        click.echo(f"queued {NOOP_JOB_TYPE} job id={job_id}")

    @jobs.command("status")
    def status() -> None:
        """Show job counts by status."""
        rows = db.session.execute(
            select(Job.status, func.count()).group_by(Job.status).order_by(Job.status)
        ).all()
        for job_status, count in rows:
            click.echo(f"{job_status}: {count}")
        if not rows:
            click.echo("no jobs")
