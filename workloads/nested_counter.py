"""
Per-thread stats counter with `threading.RLock`-guarded nested API.

Each thread owns a `StatsCounter` instance whose public methods all
acquire the same `RLock`. The outer methods call inner methods that
re-acquire the lock.
"""

from __future__ import annotations

import threading

import common

BATCHES_PER_THREAD = common.scaled(40_000, 4_000)
INCREMENTS_PER_BATCH = 25

BENCH_SPEC = {
    "name": "nested_counter",
    "description": "Per-thread stats counter with RLock-guarded nested public/private methods.",
    "num_threads": common.NUM_THREADS,
    "sync": "rlock",
    "work_units": common.NUM_THREADS
    * BATCHES_PER_THREAD
    * INCREMENTS_PER_BATCH,
}


class StatsCounter:
    """
    Monitor-pattern counter: every public method locks the same RLock,
    and outer methods call inner methods that re-acquire the lock.
    """

    __slots__ = ("lock", "_total", "_max", "_min")

    def __init__(self) -> None:
        self.lock = threading.RLock()
        self._total = 0
        self._max = 0
        self._min = 10**18

    def bump(self, n: int) -> None:
        with self.lock:
            self._total = (self._total + n) % 10_000_019
            if n > self._max:
                self._max = n
            if n < self._min:
                self._min = n

    def add_batch(self, values: list[int]) -> int:
        with self.lock:
            # Re-enters the same RLock for each call to bump().
            for v in values:
                self.bump(v)
            return self.snapshot()

    def snapshot(self) -> int:
        with self.lock:
            return (self._total + self._max + self._min) % 10_000_019


def _drive_counter(tid: int) -> int:
    c = StatsCounter()
    last = 0
    for b in range(BATCHES_PER_THREAD):
        base = tid * 7919 + b * 31
        values = [
            (base + i * 13) % 1000 + 1 for i in range(INCREMENTS_PER_BATCH)
        ]
        last = c.add_batch(values)
    return last


def main_parallel() -> int:
    parts = [0] * common.NUM_THREADS

    def worker(tid: int, _item: int) -> int:
        parts[tid] = _drive_counter(tid)
        return parts[tid]

    common.parallel_for(worker, list(range(common.NUM_THREADS)))
    return sum(parts) % 10_000_019


def main_serial() -> int:
    return (
        sum(_drive_counter(tid) for tid in range(common.NUM_THREADS))
        % 10_000_019
    )


if __name__ == "__main__":
    common.run_entry(main_parallel, main_serial)
