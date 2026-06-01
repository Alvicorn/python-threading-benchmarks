"""
Composite Simpson's rule numerical integration of a non-trivial f(x).

Integrand: f(x) = sin(x) * exp(-x/10) + cos(x*x). Since there is no
closed-form solution, use Simpson's rule with N panels. Each thread
integrates a disjoint sub-range before accumulating the results for
the answer.

Embarrassingly parallel: per-thread accumulator, zero shared writes.
"""

from __future__ import annotations

import math

import common

PANELS_PER_THREAD = common.scaled(400_000, 40_000)  # must be even
A_LIMIT = 0.0
B_LIMIT = 50.0

# Total panels across all threads; ensure even for Simpson's rule.
_TOTAL_PANELS = PANELS_PER_THREAD * common.NUM_THREADS
assert _TOTAL_PANELS % 2 == 0, "Simpson's rule needs an even panel count"

BENCH_SPEC = {
    "name": "numerical_integration",
    "description": "Composite Simpson's rule on f(x)=sin(x)e^(-x/10)+cos(x^2); range partitioned.",
    "num_threads": common.NUM_THREADS,
    "sync": "none",
    "work_units": _TOTAL_PANELS,
}


def _f(x: float) -> float:
    return math.sin(x) * math.exp(-x / 10.0) + math.cos(x * x)


def _simpson_range(a: float, b: float, panels: int) -> float:
    """
    Composite Simpson's rule over [a, b] with `panels` even panels.
    """
    h = (b - a) / panels
    s = _f(a) + _f(b)
    for i in range(1, panels):
        x = a + i * h
        s += (4.0 if (i & 1) else 2.0) * _f(x)
    return s * h / 3.0


def _slice(tid: int) -> tuple[float, float, int]:
    width = (B_LIMIT - A_LIMIT) / common.NUM_THREADS
    a = A_LIMIT + tid * width
    b = a + width
    return (a, b, PANELS_PER_THREAD)


def _integrate_slice(tid: int) -> float:
    a, b, panels = _slice(tid)
    return _simpson_range(a, b, panels)


def main_parallel() -> int:
    partials = [0.0] * common.NUM_THREADS

    def worker(tid: int, _item: int) -> int:
        partials[tid] = _integrate_slice(tid)
        return 0

    common.parallel_for(worker, list(range(common.NUM_THREADS)))
    return int(abs(sum(partials)) * 1e9) % 10_000_019


def main_serial() -> int:
    total = sum(_integrate_slice(tid) for tid in range(common.NUM_THREADS))
    return int(abs(total) * 1e9) % 10_000_019


if __name__ == "__main__":
    common.run_entry(main_parallel, main_serial)
