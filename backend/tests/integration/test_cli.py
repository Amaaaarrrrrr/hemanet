from flask import Flask
from sqlalchemy import select

from app.extensions import db
from app.jobs.builtin import NOOP_JOB_TYPE
from app.jobs.models import Job


def test_enqueue_noop_and_status(app: Flask) -> None:
    runner = app.test_cli_runner()

    result = runner.invoke(args=["jobs", "enqueue-noop"])
    status = runner.invoke(args=["jobs", "status"])

    assert result.exit_code == 0 and "queued system.noop" in result.output
    assert db.session.scalars(select(Job.job_type)).all() == [NOOP_JOB_TYPE]
    assert "QUEUED: 1" in status.output
