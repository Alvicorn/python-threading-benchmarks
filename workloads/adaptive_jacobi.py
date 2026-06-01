"""
Adaptive Jacobi linear solver with `threading.Condition` coordination.

Solve Ax = b for a small diagonally-dominant A using Jacobi iteration.
Workers each own a slice of the unknown vector x; per iteration they
read the previous x to compute their slice of the next x and the local
maximum residual.

A `Condition` coordinates phases: each worker `notify`s under the cv
after posting its slice's residual. A designated "coordinator" role
(tid=0, also doing real work) `wait_for(...)` until all workers have
posted, then computes the global maximum residual, decides convergence
or another iteration, swaps the read/write buffers, and `notify_all()`s
to release the workers into the next iteration.
"""

from __future__ import annotations

import random
import threading

import common

N = common.scaled(320, 40)  # system size
MAX_ITERS = common.scaled(300, 60)
TOLERANCE = 1e-6

BENCH_SPEC = {
    "name": "adaptive_jacobi",
    "description": "Adaptive Jacobi linear solver; Condition coordinates iteration phases.",
    "num_threads": common.NUM_THREADS,
    "sync": "condition",
    "work_units": N * N * MAX_ITERS,
}


def _build_system(
    n: int, seed: int = 73
) -> tuple[list[list[float]], list[float]]:
    rng = random.Random(seed)
    A = [[rng.uniform(-1.0, 1.0) for _ in range(n)] for _ in range(n)]
    # Make strictly diagonally dominant (guarantees Jacobi convergence).
    for i in range(n):
        A[i][i] = sum(abs(A[i][j]) for j in range(n) if j != i) + 2.0
    b = [rng.uniform(-5.0, 5.0) for _ in range(n)]
    return A, b


def _update_range(
    start: int,
    stop: int,
    A: list[list[float]],
    b: list[float],
    x_old: list[float],
    x_new: list[float],
) -> float:
    """
    Compute x_new[start:stop] from x_old; return local max |x_new - x_old|.
    """
    local_max = 0.0
    for i in range(start, stop):
        Ai = A[i]
        s = 0.0
        for j in range(N):
            if j != i:
                s += Ai[j] * x_old[j]
        nv = (b[i] - s) / Ai[i]
        x_new[i] = nv
        d = abs(nv - x_old[i])
        if d > local_max:
            local_max = d
    return local_max


def _checksum(x: list[float]) -> int:
    s = 0.0
    for i, v in enumerate(x):
        s += (i + 1) * v
    return int(abs(s) * 1e6) % 10_000_019


def main_parallel() -> int:
    A, b = _build_system(N)
    bufs = [[0.0] * N, [0.0] * N]  # ping-pong: bufs[g & 1] is current
    nt = common.NUM_THREADS

    cv = threading.Condition()
    residuals: list[float] = [0.0] * nt
    # All three boxed so the predicate / coordinator can read+write safely.
    iteration_box = [0]
    posted_count_box = [0]
    done_box = [False]
    final_iter_box = [0]

    def slice_of(tid: int) -> tuple[int, int]:
        chunk = (N + nt - 1) // nt
        start = tid * chunk
        return (start, min(start + chunk, N))

    def worker(tid: int, _item: int) -> int:
        start, stop = slice_of(tid)
        while True:
            with cv:
                if done_box[0]:
                    return 0
                cur_iter = iteration_box[0]
                src = bufs[cur_iter & 1]
                dst = bufs[(cur_iter + 1) & 1]
            # Heavy work outside the lock
            r = _update_range(start, stop, A, b, src, dst)
            with cv:
                residuals[tid] = r
                posted_count_box[0] += 1
                if posted_count_box[0] == nt:
                    # Coordinator role: decide convergence, advance iter
                    max_r = max(residuals)
                    if max_r < TOLERANCE or iteration_box[0] + 1 >= MAX_ITERS:
                        done_box[0] = True
                        final_iter_box[0] = iteration_box[0] + 1
                    posted_count_box[0] = 0
                    iteration_box[0] += 1
                    cv.notify_all()
                else:

                    def not_my_iter(i: int = cur_iter) -> bool:
                        return iteration_box[0] != i

                    cv.wait_for(not_my_iter)
                if done_box[0]:
                    return 0

    common.parallel_for(worker, list(range(nt)))
    final_x = bufs[final_iter_box[0] & 1]
    return _checksum(final_x)


def main_serial() -> int:
    A, b = _build_system(N)
    bufs = [[0.0] * N, [0.0] * N]
    final = 0
    for it in range(MAX_ITERS):
        src = bufs[it & 1]
        dst = bufs[(it + 1) & 1]
        r = _update_range(0, N, A, b, src, dst)
        final = it + 1
        if r < TOLERANCE:
            break
    return _checksum(bufs[final & 1])


if __name__ == "__main__":
    common.run_entry(main_parallel, main_serial)
