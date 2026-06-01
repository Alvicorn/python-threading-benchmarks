"""
Worker pool with `threading.BoundedSemaphore` permits, sum-of-squares
over chunked integer arrays per task.

Run multiple threads repeatedly computing a deterministic sum-of-squares
of large integer chucks. Each thread performs several "tasks" and before
each task, it acquires a permit.
"""

from __future__ import annotations

import threading

import common

TASKS_PER_THREAD = common.scaled(20, 4)
CHUNK_LEN = common.scaled(50_000, 5_000)

BENCH_SPEC = {
    "name": "bounded_quadsum",
    "description": "Worker pool with BoundedSemaphore permits; sum-of-squares over int chunks.",
    "num_threads": common.NUM_THREADS,
    "sync": "bounded-semaphore",
    "work_units": common.NUM_THREADS * TASKS_PER_THREAD * CHUNK_LEN,
}


def _quad_sum(tid: int, task: int) -> int:
    base = tid * 1009 + task * 7919
    s = 0
    for i in range(CHUNK_LEN):
        x = (base + i) & 0xFFFF
        s = (s + x * x) % 10_000_019
    return s


def _process_with_permit(tid: int, sem: threading.BoundedSemaphore) -> int:
    local = 0
    for task in range(TASKS_PER_THREAD):
        sem.acquire()
        try:
            local = (local + _quad_sum(tid, task)) % 10_000_019
        finally:
            sem.release()
    return local


def main_parallel() -> int:
    sem = threading.BoundedSemaphore(common.NUM_THREADS)
    results = [0] * common.NUM_THREADS

    def worker(tid: int, _item: int) -> int:
        results[tid] = _process_with_permit(tid, sem)
        return results[tid]

    common.parallel_for(worker, list(range(common.NUM_THREADS)))
    return sum(results) % 10_000_019


def main_serial() -> int:
    sem = threading.BoundedSemaphore(
        common.NUM_THREADS
    )  # constructed for parity
    total = 0
    for tid in range(common.NUM_THREADS):
        total = (total + _process_with_permit(tid, sem)) % 10_000_019
    return total


if __name__ == "__main__":
    common.run_entry(main_parallel, main_serial)
