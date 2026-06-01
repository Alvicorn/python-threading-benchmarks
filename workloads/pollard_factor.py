"""
Pollard's rho integer factorization with `threading.Event` early termination.

A composite TARGET is constructed at module load. Each thread runs
Pollard's rho with its own random starting point and `c` constant. The
first thread to find a non-trivial factor calls `Event.set()` and
writes its found factor into a shared slot. Other threads poll the
event every POLL_EVERY iterations and exit.
"""

from __future__ import annotations

import math
import threading

import common

# Semiprime targets sized so each rho run does enough work that the
# parallel-version's thread-spawn cost is amortised:
#   FULL : ~32-bit primes → ~65k rho iterations per seed expected.
#   SMOKE: ~22-bit primes → ~2k iterations per seed expected.
# Both factors are prime, so any rho hit returns one of them. The
# checksum folds the result so parallel/serial agree regardless of
# which of the two factors was found first.
TARGET_FULL = 2_147_483_647 * 2_147_483_659  # Mersenne 2^31-1 and next prime
TARGET_SMOKE = 4_194_301 * 4_194_319  # both prime
TARGET = TARGET_FULL if not common.smoke() else TARGET_SMOKE

# Max iterations a single rho run may take before bailing on this (x0, c).
MAX_ITERS = common.scaled(2_000_000, 200_000)
POLL_EVERY = 1024

BENCH_SPEC = {
    "name": "pollard_factor",
    "description": "Pollard's rho factorization; first-to-find via Event, threads use different seeds.",
    "num_threads": common.NUM_THREADS,
    "sync": "event",
    "work_units": MAX_ITERS,  # upper bound; real work depends on luck
}


def _rho(n: int, x0: int, c: int, event: threading.Event) -> int:
    """
    One Pollard's rho run from `x0`. Returns a non-trivial factor or 0.
    """
    x = x0
    y = x0
    d = 1
    iters = 0
    while d == 1:
        iters += 1
        if iters > MAX_ITERS:
            return 0
        if (iters & (POLL_EVERY - 1)) == 0 and event.is_set():
            return 0
        x = (x * x + c) % n
        y = (y * y + c) % n
        y = (y * y + c) % n
        d = math.gcd(abs(x - y), n)
    if d == n:
        return 0
    return d


class Found:
    __slots__ = ("factor", "lock")

    def __init__(self) -> None:
        self.factor: int = 0
        self.lock = threading.Lock()

    def offer(self, f: int) -> None:
        with self.lock:
            if self.factor == 0:
                self.factor = f


def _try_seeds_for_tid(tid: int, found: Found, event: threading.Event) -> None:
    # Each thread sweeps a small ladder of (x0, c) pairs deterministic in tid.
    for k in range(64):
        if event.is_set():
            return
        x0 = (2 + tid * 17 + k * 101) % (TARGET - 2)
        c = 1 + (tid * 7 + k * 13) % 999
        f = _rho(TARGET, x0, c, event)
        if f != 0:
            found.offer(f)
            event.set()
            return


def main_parallel() -> int:
    found = Found()
    event = threading.Event()

    def worker(tid: int, _item: int) -> int:
        _try_seeds_for_tid(tid, found, event)
        return 0

    common.parallel_for(worker, list(range(common.NUM_THREADS)))
    return _checksum(found.factor)


def main_serial() -> int:
    """
    Sequential version: try the same (tid, k) ladder in order; the
    smallest non-trivial factor of TARGET found first wins.

    Because the target is a semi-prime with both factors prime, every
    successful rho run returns one of the two primes. The checksum
    folds the result into a value independent of *which* of the two
    was found, so parallel and serial agree.
    """
    f = 0
    for tid in range(common.NUM_THREADS):
        for k in range(64):
            x0 = (2 + tid * 17 + k * 101) % (TARGET - 2)
            c = 1 + (tid * 7 + k * 13) % 999
            f = _rho(
                TARGET, x0, c, threading.Event()
            )  # dummy event, never set
            if f != 0:
                return _checksum(f)
    return _checksum(0)


def _checksum(factor: int) -> int:
    """
    Fold the factor into a value independent of which of the two primes
    was returned (TARGET = p*q; either factor maps to the same checksum).
    """
    if factor == 0:
        return 0
    other = TARGET // factor
    pair = (min(factor, other), max(factor, other))
    return (pair[0] * 31 + pair[1]) % 10_000_019


if __name__ == "__main__":
    common.run_entry(main_parallel, main_serial)
