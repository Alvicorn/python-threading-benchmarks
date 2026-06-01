"""
Monte Carlo pi: each thread draws samples with its own RNG, sums to a
per-thread accumulator, then we sum across threads at the end.

Embarrassingly parallel: no shared state between worker threads.
"""

from __future__ import annotations

import random

import common

SAMPLES_PER_THREAD = common.scaled(200_000, 20_000)

BENCH_SPEC = {
    "name": "monte_carlo_pi",
    "description": "Monte Carlo pi, embarrassingly parallel (per-thread RNG).",
    "num_threads": common.NUM_THREADS,
    "sync": "none",
    "work_units": common.NUM_THREADS * SAMPLES_PER_THREAD,
}


def _count_for_tid(tid: int) -> int:
    rng = random.Random(1337 + tid)
    c = 0
    for _ in range(SAMPLES_PER_THREAD):
        x = rng.random()
        y = rng.random()
        if x * x + y * y <= 1.0:  # point lines within the circle
            c += 1
    return c


def main_parallel() -> int:
    inside = [0] * common.NUM_THREADS

    def worker(tid: int, _item: int) -> int:
        inside[tid] = _count_for_tid(tid)
        return inside[tid]

    common.parallel_for(worker, list(range(common.NUM_THREADS)))
    return sum(inside)


def main_serial() -> int:
    return sum(_count_for_tid(tid) for tid in range(common.NUM_THREADS))


if __name__ == "__main__":
    common.run_entry(main_parallel, main_serial)
