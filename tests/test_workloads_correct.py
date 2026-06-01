"""
Each workload, smoke-sized, must be deterministic and match a golden
checksum in BOTH parallel and serial mode. The serial baseline produces
the same answer as the parallel run; any divergence is a workload bug.
"""

from __future__ import annotations

import pytest
from conftest import WORKLOADS, parse_bench_result, run_workload

# Golden checksums recorded once after initial implementation, with
# BENCH_SMOKE=1. Regenerate by running each workload with smoke and
# pasting the printed checksum.
GOLDEN = {
    "adaptive_jacobi": 5777198,
    "bfs": 912,
    "bitonic_sort": 7016758,
    "bounded_quadsum": 403974,
    "bounded_workers": 610102,
    "concurrent_hashmap": 3367217,
    "cv_bounded_buffer": 505602,
    "dining_philosophers": 96,
    "early_term_search": 88484,
    "factorization_pool": 231258,
    "fft": 3119014,
    "floyd_warshall": 607403,
    "matmul": 2491385,
    "memo_recursion": 9654971,
    "monte_carlo_pi": 125787,
    "nested_counter": 407248,
    "numerical_integration": 3987766,
    "page_rank": 9998119,
    "password_crack": 67,
    "permit_pool": 66575,
    "pollard_factor": 4217403,
    "prime_sieve": 17984,
    "priority_pipeline": 505602,
    "producer_consumer": 505602,
}

MODES = ("parallel", "serial")


def test_golden_coverage() -> None:
    """Every workload has a golden value (catches drift after add/remove)."""
    missing = set(WORKLOADS) - set(GOLDEN)
    extra = set(GOLDEN) - set(WORKLOADS)
    assert not missing, f"workloads without golden checksum: {missing}"
    assert not extra, f"golden entries with no workload: {extra}"


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("workload", WORKLOADS)
def test_workload_runs(workload: str, mode: str) -> None:
    proc = run_workload(workload, mode=mode, smoke=True)
    assert proc.returncode == 0, (
        f"{workload} ({mode}) failed: stderr={proc.stderr[-400:]}"
    )
    payload = parse_bench_result(proc.stdout)
    assert payload["time_s"] > 0
    assert payload["cpu_s"] >= 0
    assert payload["peak_mb"] > 0
    assert payload["checksum"] == GOLDEN[workload], (
        f"{workload} ({mode}) checksum drift: got {payload['checksum']!r}, "
        f"expected {GOLDEN[workload]!r}"
    )


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("workload", WORKLOADS)
def test_workload_deterministic(workload: str, mode: str) -> None:
    """Two runs back-to-back produce the same checksum."""
    proc1 = run_workload(workload, mode=mode, smoke=True)
    proc2 = run_workload(workload, mode=mode, smoke=True)
    assert proc1.returncode == 0 and proc2.returncode == 0
    a = parse_bench_result(proc1.stdout)
    b = parse_bench_result(proc2.stdout)
    assert a["checksum"] == b["checksum"], (
        f"{workload} ({mode}) non-deterministic: "
        f"{a['checksum']!r} != {b['checksum']!r}"
    )
