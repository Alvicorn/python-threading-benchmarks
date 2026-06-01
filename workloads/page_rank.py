"""
PageRank power iteration on a randomly-generated sparse graph.

NUM_THREADS each own a disjoint slice of nodes. Per iteration:
  - phase 1 (parallel): each thread reads prev_scores[v] for all v in its
    slice's in-edges and writes new_scores[v] for v in its slice.
  - barrier
  - phase 0 of next iter swaps prev/new via index.

prev_scores is read-only during an iteration; new_scores is written only
by the owning thread for its slice. Barrier between iterations. Race-free.
"""

from __future__ import annotations

import random

import common

NUM_NODES = common.scaled(16_000, 400)
AVG_OUT = common.scaled(10, 5)
ITERS = common.scaled(15, 5)
DAMPING = 0.85

BENCH_SPEC = {
    "name": "page_rank",
    "description": "PageRank power iteration on a sparse graph; barrier between iterations.",
    "num_threads": common.NUM_THREADS,
    "sync": "barrier",
    "work_units": NUM_NODES * AVG_OUT * ITERS,
}


def build_graph(n: int, avg_out: int, seed: int = 42) -> list[list[int]]:
    rng = random.Random(seed)
    in_edges: list[list[int]] = [[] for _ in range(n)]
    for u in range(n):
        k = max(1, int(rng.gauss(avg_out, 1.5)))
        for _ in range(k):
            v = rng.randrange(n)
            if v != u:
                in_edges[v].append(u)
    return in_edges


def out_degree(in_edges: list[list[int]]) -> list[int]:
    n = len(in_edges)
    out = [0] * n
    for v in range(n):
        for u in in_edges[v]:
            out[u] += 1
    for i in range(n):
        if out[i] == 0:
            out[i] = 1
    return out


def _update_range(
    start: int,
    stop: int,
    in_edges: list[list[int]],
    out_deg: list[int],
    prev: list[float],
    cur: list[float],
    base: float,
) -> None:
    for v in range(start, stop):
        s = 0.0
        for u in in_edges[v]:
            s += prev[u] / out_deg[u]
        cur[v] = base + DAMPING * s


def main_parallel() -> int:
    in_edges = build_graph(NUM_NODES, AVG_OUT)
    out_deg = out_degree(in_edges)
    scores = [1.0 / NUM_NODES] * NUM_NODES
    new_scores = [0.0] * NUM_NODES
    base = (1.0 - DAMPING) / NUM_NODES

    def worker(
        tid: int, _item: int, prev: list[float], cur: list[float]
    ) -> None:
        n = NUM_NODES
        chunk = (n + common.NUM_THREADS - 1) // common.NUM_THREADS
        start = tid * chunk
        stop = min(start + chunk, n)
        _update_range(start, stop, in_edges, out_deg, prev, cur, base)

    for _ in range(ITERS):

        def wrapped(
            tid: int,
            item: int,
            _s: list[float] = scores,
            _n: list[float] = new_scores,
        ) -> int:
            worker(tid, item, _s, _n)
            return 0

        common.parallel_for(wrapped, list(range(common.NUM_THREADS)))
        scores, new_scores = new_scores, scores
        for i in range(NUM_NODES):
            new_scores[i] = 0.0

    return int(sum(scores) * 1e9) % 10_000_019


def main_serial() -> int:
    in_edges = build_graph(NUM_NODES, AVG_OUT)
    out_deg = out_degree(in_edges)
    scores = [1.0 / NUM_NODES] * NUM_NODES
    new_scores = [0.0] * NUM_NODES
    base = (1.0 - DAMPING) / NUM_NODES

    for _ in range(ITERS):
        _update_range(
            0, NUM_NODES, in_edges, out_deg, scores, new_scores, base
        )
        scores, new_scores = new_scores, scores
        for i in range(NUM_NODES):
            new_scores[i] = 0.0

    return int(sum(scores) * 1e9) % 10_000_019


if __name__ == "__main__":
    common.run_entry(main_parallel, main_serial)
