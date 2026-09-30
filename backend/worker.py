"""HemaNet worker entry point.

PHASE E0 PLACEHOLDER: logs a heartbeat so the ``worker`` container can be
verified. The real Postgres-backed job loop arrives in Phase E1.5 (ADR-003).
"""

import logging
import os
import signal
import sys
import threading
from collections.abc import Callable
from types import FrameType

log = logging.getLogger("hemanet.worker")


def run(
    interval_seconds: float,
    max_beats: int | None = None,
    sleep: Callable[[float], object] | None = None,
    stop_event: threading.Event | None = None,
) -> int:
    """Emit heartbeats until stopped; return the number emitted.

    SIGTERM/SIGINT set ``stop_event``, which also interrupts the wait between
    beats so the container stops promptly.
    """
    stop = stop_event or threading.Event()
    wait = sleep or stop.wait

    def _stop(signum: int, _frame: FrameType | None) -> None:
        log.info("worker received signal %s, stopping", signum)
        stop.set()

    previous = {sig: signal.signal(sig, _stop) for sig in (signal.SIGTERM, signal.SIGINT)}
    beats = 0
    try:
        while not stop.is_set() and (max_beats is None or beats < max_beats):
            beats += 1
            log.info("worker heartbeat phase=E0 placeholder beat=%d", beats)
            wait(interval_seconds)
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
    return beats


def main() -> None:
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    interval = float(os.environ.get("WORKER_HEARTBEAT_SECONDS", "30"))
    run(interval)


if __name__ == "__main__":
    main()
