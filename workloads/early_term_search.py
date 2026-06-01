"""
Parallel brute-force search with early-termination via `threading.Event`.

Find the smallest n in [0, N) whose SHA-256 hex digest starts with
PREFIX. Each of NUM_THREADS scans a *stride* of [0, N): thread tid
visits indices i with i % NUM_THREADS == tid, in increasing order
within its stride. The first thread to find a match updates a shared
`best` and calls `event.set()`.

Every POLL_EVERY iterations each thread polls the event. If set AND
the current best is *smaller than* the thread's next-to-scan index,
the thread can safely exit (anything remaining in its stride is
larger than the current best, so can't improve it). This preserves
the serial smallest-match semantics while letting threads exit early.
"""

from __future__ import annotations

import hashlib
import threading

import common

N = common.scaled(2_000_000, 200_000)
PREFIX = "0000"  # ~1-in-65536 hit rate
POLL_EVERY = 256

BENCH_SPEC = {
    "name": "early_term_search",
    "description": "Parallel brute-force SHA-256 search with Event-driven early termination.",
    "num_threads": common.NUM_THREADS,
    "sync": "event",
    "work_units": N,
}


def _matches(i: int) -> bool:
    return hashlib.sha256(str(i).encode()).hexdigest().startswith(PREFIX)


class Best:
    __slots__ = ("value", "lock")

    def __init__(self) -> None:
        self.value: int = N  # sentinel: "no match yet"
        self.lock = threading.Lock()

    def offer(self, candidate: int) -> None:
        with self.lock:
            if candidate < self.value:
                self.value = candidate


def _scan_stripe(tid: int, best: Best, event: threading.Event) -> None:
    """
    Scan stripe tid in increasing order; early-exit on Event when safe.
    """
    nt = common.NUM_THREADS
    i = tid
    iters_since_poll = 0
    while i < N:
        if iters_since_poll >= POLL_EVERY:
            if event.is_set() and best.value < i:
                return
            iters_since_poll = 0
        if _matches(i):
            best.offer(i)
            event.set()
            return
        i += nt
        iters_since_poll += 1


def main_parallel() -> int:
    best = Best()
    event = threading.Event()

    def worker(tid: int, _item: int) -> int:
        _scan_stripe(tid, best, event)
        return 0

    common.parallel_for(worker, list(range(common.NUM_THREADS)))
    return best.value


def main_serial() -> int:
    """
    Sequential equivalent: walk 0..N-1 and return the smallest match.
    """
    for i in range(N):
        if _matches(i):
            return i
    return N


if __name__ == "__main__":
    common.run_entry(main_parallel, main_serial)
