"""
Worker pool with `threading.Semaphore`to manage permits, trial-division
factorization per task.

NUM_THREADS workers each process TASKS_PER_THREAD integers.Each task
acquires one permit from a `Semaphore(NUM_THREADS)`, factorizes the
integer by trial division, and releases the permit.
"""

from __future__ import annotations

import threading

import common

TASKS_PER_THREAD = common.scaled(160, 16)
# Each task factorizes BASE_N + tid * 1_000_003 + i * 7_001 (deterministic).
BASE_N = common.scaled(50_000_000, 5_000_000)

BENCH_SPEC = {
    "name": "factorization_pool",
    "description": "Worker pool with Semaphore permits; trial-division factorisation per task.",
    "num_threads": common.NUM_THREADS,
    "sync": "semaphore",
    "work_units": common.NUM_THREADS * TASKS_PER_THREAD,
}


def _trial_factor(n: int) -> int:
    """
    Return a checksum-friendly fingerprint of n's smallest prime factors.
    """
    out = 0
    x = n
    if x <= 1:
        return 0
    # Strip factors of 2
    while x % 2 == 0:
        out = (out + 2) % 10_000_019
        x //= 2
    p = 3
    while p * p <= x:
        while x % p == 0:
            out = (out + p) % 10_000_019
            x //= p
        p += 2
    if x > 1:
        out = (out + x) % 10_000_019
    return out


def _process_with_permit(tid: int, sem: threading.Semaphore) -> int:
    local = 0
    for i in range(TASKS_PER_THREAD):
        n = BASE_N + tid * 1_000_003 + i * 7_001
        sem.acquire()
        try:
            local = (local + _trial_factor(n)) % 10_000_019
        finally:
            sem.release()
    return local


def main_parallel() -> int:
    sem = threading.Semaphore(common.SEMAPHORE_COUNT)
    results = [0] * common.NUM_THREADS

    def worker(tid: int, _item: int) -> int:
        results[tid] = _process_with_permit(tid, sem)
        return results[tid]

    common.parallel_for(worker, list(range(common.NUM_THREADS)))
    return sum(results) % 10_000_019


def main_serial() -> int:
    sem = threading.Semaphore(1)
    total = 0
    for tid in range(common.NUM_THREADS):
        total = (total + _process_with_permit(tid, sem)) % 10_000_019
    return total


if __name__ == "__main__":
    common.run_entry(main_parallel, main_serial)
