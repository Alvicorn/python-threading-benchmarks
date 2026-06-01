"""
Pure-Python matrix multiplication. NUM_THREADS owns disjoint row-bands of C.

Race-free: each thread reads A,B and writes only its rows of C.
"""

from __future__ import annotations

import common

DIM = common.scaled(140, 48)

BENCH_SPEC = {
    "name": "matmul",
    "description": "Pure-Python row-parallel DIM*DIM matrix multiply; no shared writes.",
    "num_threads": common.NUM_THREADS,
    "sync": "none",
    "work_units": DIM * DIM * DIM,
}


def make(seed: int) -> list[list[float]]:
    import random

    rng = random.Random(seed)
    return [[rng.uniform(-1, 1) for _ in range(DIM)] for _ in range(DIM)]


def _compute_band(
    tid: int, A: list[list[float]], B: list[list[float]], C: list[list[float]]
) -> int:
    chunk = (DIM + common.NUM_THREADS - 1) // common.NUM_THREADS
    start = tid * chunk
    stop = min(start + chunk, DIM)
    local = 0.0
    for i in range(start, stop):
        ci = C[i]
        ai = A[i]
        for j in range(DIM):
            s = 0.0
            for k in range(DIM):
                s += ai[k] * B[k][j]
            ci[j] = s
            local += s
    return int(abs(local) * 1e6) % 10_000_019


def main_parallel() -> int:
    A = make(1)
    B = make(2)
    C = [[0.0] * DIM for _ in range(DIM)]

    def worker(tid: int, _item: int) -> int:
        return _compute_band(tid, A, B, C)

    results = common.parallel_for(worker, list(range(common.NUM_THREADS)))
    return sum(results) % 10_000_019


def main_serial() -> int:
    A = make(1)
    B = make(2)
    C = [[0.0] * DIM for _ in range(DIM)]
    total = sum(
        _compute_band(tid, A, B, C) for tid in range(common.NUM_THREADS)
    )
    return total % 10_000_019


if __name__ == "__main__":
    common.run_entry(main_parallel, main_serial)
