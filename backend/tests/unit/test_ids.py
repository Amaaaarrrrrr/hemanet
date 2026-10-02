"""UUIDv7 generator (RFC 9562 §5.7, §6.2)."""

import re
import threading
import uuid

import pytest

from app.core.ids import UUIDv7Generator, new_id, timestamp_ms

UUID7_TEXT = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
T0 = 1_790_000_000_000  # a fixed millisecond timestamp in 2026


def fixed_time(value: int = T0) -> UUIDv7Generator:
    return UUIDv7Generator(time_ms=lambda: value)


def test_new_id_is_rfc9562_version_7() -> None:
    value = new_id()

    assert isinstance(value, uuid.UUID)
    assert value.version == 7
    assert value.variant == uuid.RFC_4122  # RFC 9562 keeps the 0b10 variant
    assert UUID7_TEXT.fullmatch(str(value))


def test_version_and_variant_bits() -> None:
    value = fixed_time()().int

    assert (value >> 76) & 0xF == 0b0111
    assert (value >> 62) & 0b11 == 0b10


def test_embeds_unix_millisecond_timestamp() -> None:
    assert timestamp_ms(fixed_time()()) == T0


def test_timestamp_ms_rejects_other_versions() -> None:
    with pytest.raises(ValueError, match="not a UUIDv7"):
        timestamp_ms(uuid.uuid4())


def test_ids_from_later_milliseconds_sort_after_earlier_ones() -> None:
    now = [T0]
    generator = UUIDv7Generator(time_ms=lambda: now[0])
    first = generator()
    now[0] += 1
    second = generator()

    assert first < second
    assert str(first) < str(second)  # also in canonical text form


def test_strictly_increasing_within_the_same_millisecond() -> None:
    generator = fixed_time()
    ids = [generator() for _ in range(2000)]

    assert ids == sorted(ids)
    assert len(set(ids)) == len(ids)


def test_counter_overflow_borrows_the_next_millisecond() -> None:
    generator = fixed_time()
    ids = [generator() for _ in range(10_000)]  # > 4096 per millisecond

    assert ids == sorted(ids)
    assert timestamp_ms(ids[-1]) > T0


def test_stays_monotonic_when_the_clock_goes_backwards() -> None:
    now = [T0]
    generator = UUIDv7Generator(time_ms=lambda: now[0])
    before = generator()
    now[0] -= 5_000  # wall clock stepped back 5 s
    after = generator()

    assert after > before
    assert timestamp_ms(after) == T0


def test_random_bits_differ_between_generators() -> None:
    assert fixed_time()() != fixed_time()()


def test_unique_across_many_ids() -> None:
    ids = {new_id() for _ in range(100_000)}

    assert len(ids) == 100_000


def test_unique_across_threads() -> None:
    generator = UUIDv7Generator()
    results: list[list[uuid.UUID]] = [[] for _ in range(8)]

    def produce(slot: int) -> None:
        results[slot] = [generator() for _ in range(5_000)]

    threads = [threading.Thread(target=produce, args=(i,)) for i in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    combined = [value for chunk in results for value in chunk]
    assert len(set(combined)) == 40_000
    for chunk in results:
        assert chunk == sorted(chunk)  # per-thread order follows generation order


def test_rejects_timestamps_beyond_48_bits() -> None:
    with pytest.raises(ValueError, match="out of range"):
        UUIDv7Generator(time_ms=lambda: 1 << 48)()
