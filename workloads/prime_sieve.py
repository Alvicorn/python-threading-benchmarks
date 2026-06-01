"""
Segmented Sieve of Eratosthenes.

Sequentially sieve primes up to floor(sqrt(N)) (the "base primes"), then
each thread sieves a disjoint segment of [sqrt(N), N] using those base
primes. Embarrassingly parallel after the small serial prelude.

Race-free: each thread writes only its segment's bool array.
"""

from __future__ import annotations

import math

import common

N = common.scaled(2_000_000, 200_000)

BENCH_SPEC = {
    "name": "prime_sieve",
    "description": "Segmented Sieve of Eratosthenes; base primes serial, segments parallel.",
    "num_threads": common.NUM_THREADS,
    "sync": "none",
    "work_units": N,
}


def _base_primes(limit: int) -> list[int]:
    """
    Sieve primes up to `limit` (inclusive) the simple way.
    """
    sieve = [True] * (limit + 1)
    sieve[0] = sieve[1] = False

    for p in range(2, int(math.isqrt(limit)) + 1):
        if not sieve[p]:
            continue
        for multiple in range(p * p, limit + 1, p):
            sieve[multiple] = False
    return [n for n in range(2, limit + 1) if sieve[n]]


def _sieve_segment(lo: int, hi: int, base: list[int]) -> int:
    """
    Count primes in [lo, hi).
    """
    size = hi - lo
    seg = bytearray(b"\x01" * size)
    for p in base:
        if p * p >= hi:
            break
        # first multiple of p that is >= lo and >= p*p
        start = max(p * p, ((lo + p - 1) // p) * p)
        for m in range(start, hi, p):
            seg[m - lo] = 0
    count = 0
    for i in range(size):
        if seg[i] and (lo + i) >= 2:
            count += 1
    return count


def _slice(tid: int) -> tuple[int, int]:
    """
    Return [lo, hi) for thread tid; first thread starts at 2.
    """
    base_limit = int(math.isqrt(N)) + 1
    full_lo = base_limit + 1
    full_hi = N + 1
    total = full_hi - full_lo
    chunk = (total + common.NUM_THREADS - 1) // common.NUM_THREADS
    lo = full_lo + tid * chunk
    hi = min(lo + chunk, full_hi)
    return (lo, hi)


def _count_for_tid(tid: int, base: list[int]) -> int:
    lo, hi = _slice(tid)
    if lo >= hi:
        return 0
    return _sieve_segment(lo, hi, base)


def main_parallel() -> int:
    base = _base_primes(int(math.isqrt(N)) + 1)

    def worker(tid: int, _item: int) -> int:
        return _count_for_tid(tid, base)

    results = common.parallel_for(worker, list(range(common.NUM_THREADS)))
    return (len(base) + sum(results)) % 10_000_019


def main_serial() -> int:
    base = _base_primes(int(math.isqrt(N)) + 1)
    total = sum(_count_for_tid(tid, base) for tid in range(common.NUM_THREADS))
    return (len(base) + total) % 10_000_019


if __name__ == "__main__":
    common.run_entry(main_parallel, main_serial)
