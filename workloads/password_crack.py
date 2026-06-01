"""
Hash search: count integers in [0, N) whose SHA-256 hex digest starts
with a target prefix. Each of NUM_THREADS workers scans a disjoint slice.
Race-free (per-thread accumulator).
"""

from __future__ import annotations

import hashlib

import common

N = common.scaled(200_000, 20_000)
PREFIX = "00"  # ~256-in-65536 hit rate

BENCH_SPEC = {
    "name": "password_crack",
    "description": "Brute-force SHA-256 hash search; per-thread counters, no shared writes.",
    "num_threads": common.NUM_THREADS,
    "sync": "none",
    "work_units": N,
}


def _count_slice(tid: int) -> int:
    chunk = (N + common.NUM_THREADS - 1) // common.NUM_THREADS
    start = tid * chunk
    stop = min(start + chunk, N)
    c = 0
    for i in range(start, stop):
        h = hashlib.sha256(str(i).encode()).hexdigest()
        if h.startswith(PREFIX):
            c += 1
    return c


def main_parallel() -> int:
    counts = [0] * common.NUM_THREADS

    def worker(tid: int, _item: int) -> int:
        counts[tid] = _count_slice(tid)
        return counts[tid]

    common.parallel_for(worker, list(range(common.NUM_THREADS)))
    return sum(counts)


def main_serial() -> int:
    return sum(_count_slice(tid) for tid in range(common.NUM_THREADS))


if __name__ == "__main__":
    common.run_entry(main_parallel, main_serial)
