"""
Level-parallel BFS on a generated random graph.

Per level: NUM_THREADS partition the current frontier; each thread walks
its slice and gathers candidate next-frontier nodes into its own list.
After `parallel_for` joins, the main thread merges the local lists into
`visited` and `next_frontier` — no lock needed because all worker
threads have finished writing before the merge starts.
"""

from __future__ import annotations

import random

import common

N = common.scaled(2_500, 500)
DEG = 96

BENCH_SPEC = {
    "name": "bfs",
    "description": "Level-parallel BFS on a random graph; per-thread frontiers merged after the parallel_for join.",
    "num_threads": common.NUM_THREADS,
    "sync": "none",
    "work_units": N * DEG,
}


def build_graph(n: int, deg: int, seed: int = 17) -> list[list[int]]:
    rng = random.Random(seed)
    adj: list[list[int]] = [[] for _ in range(n)]
    for u in range(n):
        for _ in range(deg):
            v = rng.randrange(n)
            if v != u:
                adj[u].append(v)
    return adj


def main_parallel() -> int:
    adj = build_graph(N, DEG)
    visited = [False] * N
    visited[0] = True
    frontier = [0]
    depth_sum = 0
    depth = 0

    while frontier:
        next_frontier: list[int] = []
        local_frontiers: list[list[int]] = [
            [] for _ in range(common.NUM_THREADS)
        ]

        def worker(
            tid: int,
            _item: int,
            f: list[int] = frontier,
            lf: list[list[int]] = local_frontiers,
        ) -> int:
            chunk = (len(f) + common.NUM_THREADS - 1) // common.NUM_THREADS
            start = tid * chunk
            stop = min(start + chunk, len(f))
            local: list[int] = []
            for idx in range(start, stop):
                u = f[idx]
                for v in adj[u]:
                    local.append(v)
            lf[tid] = local
            return 0

        common.parallel_for(worker, list(range(common.NUM_THREADS)))
        # parallel_for has joined; main thread is the sole writer below,
        # so no lock is needed for the merge step.
        for local in local_frontiers:
            for v in local:
                if not visited[v]:
                    visited[v] = True
                    next_frontier.append(v)
        depth += 1
        depth_sum += depth * len(next_frontier)
        frontier = next_frontier

    return depth_sum % 10_000_019


def main_serial() -> int:
    adj = build_graph(N, DEG)
    visited = [False] * N
    visited[0] = True
    frontier = [0]
    depth_sum = 0
    depth = 0

    while frontier:
        next_frontier: list[int] = []
        nt = common.NUM_THREADS
        chunk = (len(frontier) + nt - 1) // nt
        for tid in range(nt):
            start = tid * chunk
            stop = min(start + chunk, len(frontier))
            for idx in range(start, stop):
                u = frontier[idx]
                for v in adj[u]:
                    if not visited[v]:
                        visited[v] = True
                        next_frontier.append(v)
        depth += 1
        depth_sum += depth * len(next_frontier)
        frontier = next_frontier

    return depth_sum % 10_000_019


if __name__ == "__main__":
    common.run_entry(main_parallel, main_serial)
