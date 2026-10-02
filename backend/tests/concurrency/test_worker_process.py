"""The real ``worker.py`` process shuts down gracefully on SIGTERM."""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest
from flask import Flask
from sqlalchemy import func, select

from app.extensions import db
from app.jobs.models import WorkerHeartbeat

pytestmark = pytest.mark.concurrency
BACKEND = Path(__file__).resolve().parents[2]


def heartbeats() -> int:
    db.session.expire_all()
    return db.session.scalar(select(func.count()).select_from(WorkerHeartbeat)) or 0


def test_sigterm_stops_worker_cleanly(real_app: Flask, migrated_database: str) -> None:
    env = os.environ | {
        "APP_ENV": "ci",
        "DATABASE_URL": migrated_database,
        "WORKER_POLL_SECONDS": "30",
        "LOG_FORMAT": "json",
    }
    process = subprocess.Popen(
        [sys.executable, "worker.py"], cwd=BACKEND, env=env, stdout=subprocess.PIPE, text=True
    )
    try:
        deadline = time.monotonic() + 15
        while heartbeats() == 0 and time.monotonic() < deadline:
            time.sleep(0.1)
        assert heartbeats() == 1

        started = time.monotonic()
        process.send_signal(signal.SIGTERM)
        exit_code = process.wait(timeout=10)

        assert exit_code == 0
        assert time.monotonic() - started < 5  # not waiting out the 30 s poll interval
        assert heartbeats() == 0
        output = process.stdout.read() if process.stdout else ""
        assert "worker stopped" in output
    finally:
        if process.poll() is None:
            process.kill()
