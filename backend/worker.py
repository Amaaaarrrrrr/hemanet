"""Entry point for the ``worker`` process: ``python worker.py``."""

import signal
from datetime import timedelta
from types import FrameType

import structlog

from app import create_app
from app.config import get_settings
from app.core.clock import get_clock
from app.extensions import db
from app.jobs.worker import Worker

log = structlog.get_logger("hemanet.worker")


def main() -> None:
    app = create_app()
    with app.app_context():
        settings = get_settings()
        worker = Worker(
            session=lambda: db.session,
            clock=get_clock(),
            poll_interval=settings.worker_poll_seconds,
            heartbeat_interval=settings.worker_heartbeat_seconds,
            lock_for=timedelta(seconds=settings.job_lock_seconds),
        )

        def _stop(signum: int, _frame: FrameType | None) -> None:
            log.info("worker received signal, finishing current work", signal=signum)
            worker.stop()

        signal.signal(signal.SIGTERM, _stop)
        signal.signal(signal.SIGINT, _stop)
        worker.run_forever()


if __name__ == "__main__":
    main()
