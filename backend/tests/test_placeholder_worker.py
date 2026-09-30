"""Smoke tests for the Phase E0 placeholder worker (replaced in E1.5)."""

import os
import signal
import threading
import time

import pytest

from worker import run


def test_run_emits_requested_number_of_heartbeats(caplog: pytest.LogCaptureFixture) -> None:
    sleeps: list[float] = []

    with caplog.at_level("INFO", logger="hemanet.worker"):
        beats = run(interval_seconds=5, max_beats=3, sleep=sleeps.append)

    assert beats == 3
    assert sleeps == [5, 5, 5]
    assert sum("worker heartbeat" in r.message for r in caplog.records) == 3


def test_run_stops_when_stop_event_is_set() -> None:
    stop = threading.Event()

    def sleep_then_stop(_seconds: float) -> None:
        stop.set()

    beats = run(interval_seconds=30, sleep=sleep_then_stop, stop_event=stop)

    assert beats == 1


def test_sigterm_interrupts_wait_between_beats() -> None:
    timer = threading.Timer(0.2, os.kill, args=(os.getpid(), signal.SIGTERM))
    timer.start()
    started = time.monotonic()

    beats = run(interval_seconds=30)

    assert beats == 1
    assert time.monotonic() - started < 5
