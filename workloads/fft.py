"""
Iterative Cooley-Tukey radix-2 FFT, NUM_THREADS with a barrier per stage.

Bit-reverse permutation done sequentially before the threads spin up.
Then for each stage (m = 2, 4, 8, …, N): the array is partitioned into
groups of size m; each group is independent. NUM_THREADS partition the
*group index* so each m-block is owned by exactly one thread. Barrier
between stages.

Race-free: within one stage, each thread writes disjoint m-blocks.
"""

from __future__ import annotations

import cmath
import math
import random
import threading

import common

LOG_N = common.scaled(16, 8)  # full 65536, smoke 256
N = 1 << LOG_N

BENCH_SPEC = {
    "name": "fft",
    "description": "Iterative Cooley-Tukey radix-2 FFT with a barrier per stage.",
    "num_threads": common.NUM_THREADS,
    "sync": "barrier",
    "work_units": N * LOG_N,
}


def bit_reverse_indices(n: int) -> list[int]:
    bits = n.bit_length() - 1
    out = []
    for i in range(n):
        r = 0
        x = i
        for _ in range(bits):
            r = (r << 1) | (x & 1)
            x >>= 1
        out.append(r)
    return out


def _setup() -> list[complex]:
    rng = random.Random(23)
    a: list[complex] = [
        complex(rng.uniform(-1, 1), rng.uniform(-1, 1)) for _ in range(N)
    ]
    rev = bit_reverse_indices(N)
    for i, r in enumerate(rev):
        if r > i:
            a[i], a[r] = a[r], a[i]
    return a


def _checksum(a: list[complex]) -> int:
    total = 0
    for i in range(N):
        total = (total + int(abs(a[i]) * 1000) * (i + 1)) % 10_000_019
    return total


def main_parallel() -> int:
    a = _setup()

    def stage_step(tid: int, barrier: threading.Barrier) -> None:
        m = 2
        while m <= N:
            half = m >> 1
            num_groups = N // m
            chunk_g = (
                num_groups + common.NUM_THREADS - 1
            ) // common.NUM_THREADS
            start_g = tid * chunk_g
            stop_g = min(start_g + chunk_g, num_groups)
            w_step = cmath.exp(-2j * math.pi / m)
            for g in range(start_g, stop_g):
                base = g * m
                w = 1 + 0j
                for j in range(half):
                    u = a[base + j]
                    v = a[base + j + half] * w
                    a[base + j] = u + v
                    a[base + j + half] = u - v
                    w *= w_step
            barrier.wait()
            m <<= 1

    common.barrier_workers(stage_step)
    return _checksum(a)


def main_serial() -> int:
    a = _setup()
    m = 2
    while m <= N:
        half = m >> 1
        num_groups = N // m
        w_step = cmath.exp(-2j * math.pi / m)
        for g in range(num_groups):
            base = g * m
            w = 1 + 0j
            for j in range(half):
                u = a[base + j]
                v = a[base + j + half] * w
                a[base + j] = u + v
                a[base + j + half] = u - v
                w *= w_step
        m <<= 1
    return _checksum(a)


if __name__ == "__main__":
    common.run_entry(main_parallel, main_serial)
