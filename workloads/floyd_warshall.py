"""
Floyd-Warshall all-pairs shortest paths, NUM_THREADS-way parallel on the `i` dim.

For each k: NUM_THREADS partition the i loop. Each thread reads 
dist[i][k], dist[k][j], and writes dist[i][j]. Barrier
between k-iterations.
"""

from __future__ import annotations

import random
import threading

import common

N = common.scaled(192, 32)
INF = 10**9

BENCH_SPEC = {
    "name": "floyd_warshall",
    "description": "Floyd-Warshall all-pairs shortest paths, i-dim parallel with barrier per k.",
    "num_threads": common.NUM_THREADS,
    "sync": "barrier",
    "work_units": N * N * N,
}


def build(n: int, seed: int = 19) -> list[list[int]]:
    rng = random.Random(seed)
    dist = [[INF] * n for _ in range(n)]
    for i in range(n):
        dist[i][i] = 0
    for _ in range(n * 6):
        u = rng.randrange(n)
        v = rng.randrange(n)
        if u != v:
            w = rng.randint(1, 50)
            if w < dist[u][v]:
                dist[u][v] = w
    return dist


def _checksum(dist: list[list[int]]) -> int:
    total = 0
    for i in range(N):
        for j in range(N):
            v = dist[i][j]
            if v < INF:
                total = (total + v * (i + 1)) % 10_000_019
    return total


def main_parallel() -> int:
    dist = build(N)

    def step(tid: int, barrier: threading.Barrier) -> None:
        chunk = (N + common.NUM_THREADS - 1) // common.NUM_THREADS
        start = tid * chunk
        stop = min(start + chunk, N)
        for k in range(N):
            dk = dist[k]
            for i in range(start, stop):
                di = dist[i]
                dik = di[k]
                if dik >= INF:
                    continue
                for j in range(N):
                    nd = dik + dk[j]
                    if nd < di[j]:
                        di[j] = nd
            barrier.wait()

    common.barrier_workers(step)
    return _checksum(dist)


def main_serial() -> int:
    dist = build(N)
    for k in range(N):
        dk = dist[k]
        for i in range(N):
            di = dist[i]
            dik = di[k]
            if dik >= INF:
                continue
            for j in range(N):
                nd = dik + dk[j]
                if nd < di[j]:
                    di[j] = nd
    return _checksum(dist)


if __name__ == "__main__":
    common.run_entry(main_parallel, main_serial)
