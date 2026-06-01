"""
Worker pool with `threading.BoundedSemaphore` to manage permits.

Per-task work is polynomial evaluation via Horner's method (distinct
from `permit_pool`'s SHA-256 hashing so the two workloads aren't
trivial copies).
"""

from __future__ import annotations

import random
import threading

import common

TASKS_PER_THREAD = common.scaled(8, 2)
POLY_DEGREE = common.scaled(2_000, 400)
EVAL_POINTS = common.scaled(500, 100)

BENCH_SPEC = {
    "name": "bounded_workers",
    "description": "Worker pool with BoundedSemaphore permits; Horner polynomial evaluation per task.",
    "num_threads": common.NUM_THREADS,
    "sync": "bounded-semaphore",
    "work_units": common.NUM_THREADS
    * TASKS_PER_THREAD
    * POLY_DEGREE
    * EVAL_POINTS,
}


def _make_polynomial(tid: int, task: int) -> list[float]:
    """
    Deterministic per-(tid, task) polynomial coefficients.
    """
    rng = random.Random(tid * 1009 + task * 31)
    return [rng.uniform(-1.0, 1.0) for _ in range(POLY_DEGREE)]


def _horner(coeffs: list[float], x: float) -> float:
    """
    Evaluate polynomial at x via Horner's method.
    """
    result = 0.0
    for c in coeffs:
        result = result * x + c
    return result


def _process_with_permit(tid: int, sem: threading.BoundedSemaphore) -> int:
    local = 0.0
    for task in range(TASKS_PER_THREAD):
        sem.acquire()
        try:
            coeffs = _make_polynomial(tid, task)
            for k in range(EVAL_POINTS):
                x = (k / EVAL_POINTS) * 2.0 - 1.0
                local += _horner(coeffs, x)
        finally:
            sem.release()
    return int(abs(local) * 1000) % 10_000_019


def main_parallel() -> int:
    sem = threading.BoundedSemaphore(common.SEMAPHORE_COUNT)
    results = [0] * common.NUM_THREADS

    def worker(tid: int, _item: int) -> int:
        results[tid] = _process_with_permit(tid, sem)
        return results[tid]

    common.parallel_for(worker, list(range(common.NUM_THREADS)))
    return sum(results) % 10_000_019


def main_serial() -> int:
    sem = threading.BoundedSemaphore(1)
    total = 0
    for tid in range(common.NUM_THREADS):
        total = (total + _process_with_permit(tid, sem)) % 10_000_019
    return total


if __name__ == "__main__":
    common.run_entry(main_parallel, main_serial)
