"""
Dining philosophers, NUM_THREADS philosophers + NUM_THREADS forks.

Each philosopher acquires its forks in ascending lock-id order (the
classic resource-hierarchy deadlock prevention). "Eat" runs a small CPU
kernel (sum of i*i mod prime) so the workload isn't pure lock pinging.

Race-free: each philosopher only touches its `meals_eaten` counter; the
forks are guarded by locks.
"""

from __future__ import annotations

import threading

import common

ROUNDS = common.scaled(120, 12)
EAT_WORK = common.scaled(1_600, 100)

BENCH_SPEC = {
    "name": "dining_philosophers",
    "description": "Classic dining philosophers; resource-hierarchy locking prevents deadlock.",
    "num_threads": common.NUM_THREADS,
    "sync": "fork-locks",
    "work_units": common.NUM_THREADS * ROUNDS,
}


class Philosopher:
    __slots__ = ("meals_eaten",)

    def __init__(self) -> None:
        self.meals_eaten = 0


def _eat_kernel() -> int:
    s = 0
    for i in range(EAT_WORK):
        s = (s + i * i) % 10_000_019
    return s


def main_parallel() -> int:
    n = common.NUM_THREADS
    forks = [threading.Lock() for _ in range(n)]
    phils = [Philosopher() for _ in range(n)]

    def live(pid: int) -> None:
        left = pid
        right = (pid + 1) % n
        a, b = (left, right) if left < right else (right, left)
        for _ in range(ROUNDS):
            with forks[a]:
                with forks[b]:
                    _eat_kernel()
                    phils[pid].meals_eaten += 1

    threads = [threading.Thread(target=live, args=(pid,)) for pid in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    total = 0
    for p in phils:
        total += p.meals_eaten
    return total


def main_serial() -> int:
    """
    Same total work as the parallel version, with no locks or threads.
    """
    n = common.NUM_THREADS
    phils = [Philosopher() for _ in range(n)]
    for pid in range(n):
        for _ in range(ROUNDS):
            _eat_kernel()
            phils[pid].meals_eaten += 1
    total = 0
    for p in phils:
        total += p.meals_eaten
    return total


if __name__ == "__main__":
    common.run_entry(main_parallel, main_serial)
