"""
Bitonic sort, NUM_THREADS with a barrier between stages.

The classic non-recursive structure: for each (k, j) outer pair, every
index i performs a compare-swap with i^j when (i & k) == 0 means ascending,
else descending. Threads partition the index space evenly. Each stage's
compare-swaps touch disjoint index pairs because j is a fixed XOR mask
within the stage.
"""

from __future__ import annotations

import random
import threading

import common

LOG_N = common.scaled(16, 8)  # full 65536, smoke 256
N = 1 << LOG_N

BENCH_SPEC = {
    "name": "bitonic_sort",
    "description": "Bitonic sort with a barrier between every stage.",
    "num_threads": common.NUM_THREADS,
    "sync": "barrier",
    "work_units": N * LOG_N * LOG_N,
}


def _make_data() -> list[int]:
    rng = random.Random(5)
    return [rng.randrange(1_000_000) for _ in range(N)]


def _checksum(data: list[int]) -> int:
    for i in range(N - 1):
        if data[i] > data[i + 1]:
            raise AssertionError(
                f"not sorted at {i}: {data[i]} > {data[i + 1]}"
            )
    s = 0
    for i, v in enumerate(data):
        s = (s + i * v) % 10_000_019
    return s


def main_parallel() -> int:
    data = _make_data()

    def stage(tid: int, barrier: threading.Barrier) -> None:
        chunk = (N + common.NUM_THREADS - 1) // common.NUM_THREADS
        start = tid * chunk
        stop = min(start + chunk, N)
        k = 2
        while k <= N:
            j = k >> 1
            while j > 0:
                for i in range(start, stop):
                    ixj = i ^ j
                    if ixj > i:
                        ascending = (i & k) == 0
                        a = data[i]
                        b = data[ixj]
                        if (ascending and a > b) or (
                            (not ascending) and a < b
                        ):
                            data[i] = b
                            data[ixj] = a
                j >>= 1
                barrier.wait()
            k <<= 1

    common.barrier_workers(stage)
    return _checksum(data)


def main_serial() -> int:
    data = _make_data()
    k = 2
    while k <= N:
        j = k >> 1
        while j > 0:
            for i in range(N):
                ixj = i ^ j
                if ixj > i:
                    ascending = (i & k) == 0
                    a = data[i]
                    b = data[ixj]
                    if (ascending and a > b) or ((not ascending) and a < b):
                        data[i] = b
                        data[ixj] = a
            j >>= 1
        k <<= 1
    return _checksum(data)


if __name__ == "__main__":
    common.run_entry(main_parallel, main_serial)
