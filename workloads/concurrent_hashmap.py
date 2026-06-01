"""
Striped concurrent hashmap: N_STRIPES dict stripes, one lock per stripe.

NUM_THREADS workers each do INSERTS_PER_THREAD inserts followed by
LOOKUPS_PER_THREAD lookups. Keys are seeded per-thread so collisions on
the same stripe are common but writes to the same key from two threads
don't happen.

Race-free under per-stripe lock.
"""

from __future__ import annotations

import threading

import common

INSERTS_PER_THREAD = common.scaled(4_000, 400)
LOOKUPS_PER_THREAD = common.scaled(4_000, 400)
N_STRIPES = 16

BENCH_SPEC = {
    "name": "concurrent_hashmap",
    "description": "Striped concurrent hashmap; one lock per stripe.",
    "num_threads": common.NUM_THREADS,
    "sync": "striped-lock",
    "work_units": common.NUM_THREADS
    * (INSERTS_PER_THREAD + LOOKUPS_PER_THREAD),
}


class Striped:
    def __init__(self) -> None:
        self.stripes: list[dict[int, int]] = [{} for _ in range(N_STRIPES)]
        self.locks: list[threading.Lock] = [
            threading.Lock() for _ in range(N_STRIPES)
        ]

    def put(self, k: int, v: int) -> None:
        idx = k % N_STRIPES
        with self.locks[idx]:
            self.stripes[idx][k] = v

    def get(self, k: int) -> int:
        idx = k % N_STRIPES
        with self.locks[idx]:
            return self.stripes[idx].get(k, -1)


def _do_thread_work(tid: int, m: Striped) -> int:
    base = tid * 10_000_000
    for i in range(INSERTS_PER_THREAD):
        k = base + i
        m.put(k, k ^ 0x5A5A5A5A)
    s = 0
    for i in range(LOOKUPS_PER_THREAD):
        k = base + (i * 7919) % INSERTS_PER_THREAD
        v = m.get(k)
        s = (s + v) % 10_000_019
    return s


def _checksum(m: Striped, found_sum: list[int]) -> int:
    total = sum(found_sum) % 10_000_019
    for st in m.stripes:
        total = (total + len(st)) % 10_000_019
    return total


def main_parallel() -> int:
    m = Striped()
    found_sum = [0] * common.NUM_THREADS

    def worker(tid: int, _item: int) -> int:
        s = _do_thread_work(tid, m)
        found_sum[tid] = s
        return s

    common.parallel_for(worker, list(range(common.NUM_THREADS)))
    return _checksum(m, found_sum)


def main_serial() -> int:
    m = Striped()
    found_sum = [0] * common.NUM_THREADS
    for tid in range(common.NUM_THREADS):
        found_sum[tid] = _do_thread_work(tid, m)
    return _checksum(m, found_sum)


if __name__ == "__main__":
    common.run_entry(main_parallel, main_serial)
