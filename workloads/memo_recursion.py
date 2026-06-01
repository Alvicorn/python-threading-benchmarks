"""
Parallel memoized recursive function with per-thread RLock cache.

Each thread runs K_QUERIES queries `f(n)` where `n` is drawn from a
per-thread RNG bounded to [0, MAX_N]. `f` is the Tribonacci-style
recurrence f(n) = f(n-1) + f(n-2) + f(n-3) mod prime. The result for
each n is memoized in a per-thread dict guarded by `threading.RLock`.

The cache lookup is wrapped in `with self.lock:`, and the cached
function recursively calls itself from inside the lock.
"""

from __future__ import annotations

import random
import threading

import common

MAX_N = 28  # bounded recursion depth — well under Python's recursion limit
K_QUERIES = common.scaled(2_000_000, 200_000)

BENCH_SPEC = {
    "name": "memo_recursion",
    "description": "Parallel memoized recursive sum with per-thread RLock-guarded cache.",
    "num_threads": common.NUM_THREADS,
    "sync": "rlock",
    "work_units": common.NUM_THREADS * K_QUERIES,
}


class MemoCache:
    """
    Re-entrant-lock-guarded memoized recursive function.

    The recursive call from within the locked region is what makes the
    RLock necessary; a plain Lock would self-deadlock.
    """

    __slots__ = ("lock", "cache")

    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.cache: dict[int, int] = {0: 0, 1: 1, 2: 1}

    def f(self, n: int) -> int:
        with self.lock:
            cached = self.cache.get(n)
            if cached is not None:
                return cached
            # Recursive call re-enters the same RLock from the same thread.
            v = (self.f(n - 1) + self.f(n - 2) + self.f(n - 3)) % 10_000_019
            self.cache[n] = v
            return v


def _query_slice(tid: int) -> int:
    rng = random.Random(2027 + tid)
    cache = MemoCache()
    total = 0
    for _ in range(K_QUERIES):
        n = rng.randrange(MAX_N + 1)
        total = (total + cache.f(n)) % 10_000_019
    return total


def main_parallel() -> int:
    parts = [0] * common.NUM_THREADS

    def worker(tid: int, _item: int) -> int:
        parts[tid] = _query_slice(tid)
        return parts[tid]

    common.parallel_for(worker, list(range(common.NUM_THREADS)))
    return sum(parts) % 10_000_019


def main_serial() -> int:
    return (
        sum(_query_slice(tid) for tid in range(common.NUM_THREADS))
        % 10_000_019
    )


if __name__ == "__main__":
    common.run_entry(main_parallel, main_serial)
