"""
Unit tests for the pure-Python pieces of run_bench.py — parsing,
spec loading, per-mode aggregation, and speedup math. No subprocesses.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conftest import WORKLOADS  # noqa: E402

from run_bench import (  # noqa: E402
    ModeStats,
    RunResult,
    WorkloadStats,
    aggregate_mode,
    discover_workloads,
    format_spec_listing,
    format_summary_table,
    load_spec,
    parse_bench_result,
)


def test_parse_bench_result_picks_last_line() -> None:
    stdout = (
        "noise\n"
        'BENCH_RESULT {"time_s": 0.1, "cpu_s": 0.4, "peak_mb": 10, "checksum": 1}\n'
        "more noise\n"
        'BENCH_RESULT {"time_s": 0.5, "cpu_s": 2.0, "peak_mb": 20, "checksum": 2}\n'
    )
    out = parse_bench_result(stdout)
    assert out == {"time_s": 0.5, "cpu_s": 2.0, "peak_mb": 20, "checksum": 2}


def test_parse_bench_result_missing_raises() -> None:
    with pytest.raises(ValueError):
        parse_bench_result("no result here\n")


def test_parse_bench_result_malformed_raises() -> None:
    with pytest.raises(ValueError):
        parse_bench_result("BENCH_RESULT {not json}\n")


def test_discover_workloads_finds_expected() -> None:
    ws = discover_workloads()
    expected = {
        # embarrassingly parallel
        "matmul",
        "monte_carlo_pi",
        "numerical_integration",
        "password_crack",
        "prime_sieve",
        # lock
        "bfs",
        "concurrent_hashmap",
        "dining_philosophers",
        # rlock
        "memo_recursion",
        "nested_counter",
        # event
        "early_term_search",
        "pollard_factor",
        # condition
        "adaptive_jacobi",
        "cv_bounded_buffer",
        # semaphore
        "permit_pool",
        "factorization_pool",
        # bounded-semaphore
        "bounded_workers",
        "bounded_quadsum",
        # barrier
        "bitonic_sort",
        "fft",
        "floyd_warshall",
        "page_rank",
        # queue
        "producer_consumer",
        "priority_pipeline",
    }
    assert set(ws) == expected
    assert 20 <= len(ws) <= 25


@pytest.mark.parametrize("workload", WORKLOADS)
def test_each_workload_has_bench_spec(workload: str) -> None:
    spec = load_spec(workload)
    assert spec["name"] == workload
    assert isinstance(spec["description"], str) and spec["description"]
    assert int(spec["num_threads"]) >= 1
    assert isinstance(spec["sync"], str) and spec["sync"]
    assert int(spec["work_units"]) >= 1


@pytest.mark.parametrize("workload", WORKLOADS)
def test_each_workload_exposes_serial_and_parallel(workload: str) -> None:
    """Every workload module must expose main_parallel() and main_serial()."""
    import importlib

    sys.path.insert(
        0, str(Path(__file__).resolve().parent.parent / "workloads")
    )
    mod = importlib.import_module(workload)
    assert callable(getattr(mod, "main_parallel", None)), (
        f"{workload} missing main_parallel()"
    )
    assert callable(getattr(mod, "main_serial", None)), (
        f"{workload} missing main_serial()"
    )


def _spec(name: str = "a", num_threads: int = 4) -> dict:
    return {
        "name": name,
        "description": "x",
        "num_threads": num_threads,
        "sync": "none",
        "work_units": 100,
    }


def _run(
    mode: str,
    wall: float,
    cpu: float,
    peak: float,
    ck: int | None,
    ok: bool = True,
) -> RunResult:
    return RunResult(
        workload="a",
        mode=mode,
        run_index=0,
        wall_s=wall,
        cpu_s=cpu,
        peak_mb=peak,
        checksum=ck,
        ok=ok,
    )


def test_aggregate_mode_means_and_cpu_efficiency() -> None:
    runs = [
        _run("parallel", 1.0, 3.6, 10.0, 42),
        _run("parallel", 2.0, 7.2, 20.0, 42),
    ]
    ms = aggregate_mode(runs, num_threads=4)
    assert ms.n_ok == 2
    assert ms.n_total == 2
    assert ms.wall_mean == pytest.approx(1.5)
    assert ms.wall_min == pytest.approx(1.0)
    assert ms.wall_stdev == pytest.approx(0.7071, rel=1e-3)
    assert ms.cpu_mean == pytest.approx(5.4)
    assert ms.peak_mb_mean == pytest.approx(15.0)
    assert ms.cpu_efficiency == pytest.approx(0.9)  # 5.4 / (1.5 * 4)
    assert ms.checksum == 42
    assert ms.checksum_stable is True


def test_aggregate_mode_skips_failed_runs() -> None:
    runs = [
        _run("parallel", 1.0, 2.0, 10.0, 42),
        _run(
            "parallel",
            float("nan"),
            float("nan"),
            float("nan"),
            None,
            ok=False,
        ),
    ]
    ms = aggregate_mode(runs, num_threads=2)
    assert ms.n_ok == 1
    assert ms.n_total == 2
    assert ms.wall_mean == pytest.approx(1.0)


def test_aggregate_mode_all_failures_returns_nan() -> None:
    runs = [
        _run(
            "parallel",
            float("nan"),
            float("nan"),
            float("nan"),
            None,
            ok=False,
        )
    ]
    ms = aggregate_mode(runs, num_threads=4)
    assert ms.n_ok == 0
    assert math.isnan(ms.wall_mean)
    assert math.isnan(ms.cpu_efficiency)


def test_aggregate_mode_flags_unstable_checksum() -> None:
    runs = [
        _run("parallel", 1.0, 1.0, 1.0, 1),
        _run("parallel", 1.0, 1.0, 1.0, 2),
    ]
    ms = aggregate_mode(runs, num_threads=2)
    assert ms.checksum_stable is False


def _mode(wall: float, n_threads: int, ck: object = 1) -> ModeStats:
    return ModeStats(
        n_ok=2,
        n_total=2,
        wall_mean=wall,
        wall_stdev=0.0,
        wall_min=wall,
        cpu_mean=wall * n_threads,
        peak_mb_mean=10.0,
        cpu_efficiency=1.0,
        checksum=ck,
        checksum_stable=True,
    )


def test_speedup_and_parallel_efficiency() -> None:
    ws = WorkloadStats(workload="a", spec=_spec(num_threads=4))
    ws.modes["serial"] = _mode(wall=4.0, n_threads=1, ck=42)
    ws.modes["parallel"] = _mode(wall=1.0, n_threads=4, ck=42)
    assert ws.speedup == pytest.approx(4.0)
    assert ws.parallel_efficiency == pytest.approx(1.0)
    assert ws.checksum_divergence is False


def test_speedup_nan_when_missing_mode() -> None:
    ws = WorkloadStats(workload="a", spec=_spec(num_threads=4))
    ws.modes["parallel"] = _mode(wall=1.0, n_threads=4)
    assert math.isnan(ws.speedup)
    assert math.isnan(ws.parallel_efficiency)


def test_checksum_divergence_detected() -> None:
    ws = WorkloadStats(workload="a", spec=_spec(num_threads=4))
    ws.modes["serial"] = _mode(wall=4.0, n_threads=1, ck=42)
    ws.modes["parallel"] = _mode(wall=1.0, n_threads=4, ck=43)
    assert ws.checksum_divergence is True


def test_format_summary_table_both_modes() -> None:
    ws = WorkloadStats(workload="a", spec=_spec(num_threads=4))
    ws.modes["serial"] = _mode(wall=4.0, n_threads=1)
    ws.modes["parallel"] = _mode(wall=1.0, n_threads=4)
    txt = format_summary_table([ws], modes=("parallel", "serial"))
    assert "speedup" in txt
    assert "par eff" in txt
    assert "a" in txt


def test_format_summary_table_parallel_only() -> None:
    ws = WorkloadStats(workload="a", spec=_spec(num_threads=4))
    ws.modes["parallel"] = _mode(wall=1.0, n_threads=4)
    txt = format_summary_table([ws], modes=("parallel",))
    assert "cpu eff" in txt
    assert "speedup" not in txt


def test_format_summary_table_serial_only() -> None:
    ws = WorkloadStats(workload="a", spec=_spec(num_threads=4))
    ws.modes["serial"] = _mode(wall=4.0, n_threads=1)
    txt = format_summary_table([ws], modes=("serial",))
    assert "speedup" not in txt
    assert "cpu eff" not in txt


def test_format_summary_table_marks_divergence() -> None:
    ws = WorkloadStats(workload="a", spec=_spec(num_threads=4))
    ws.modes["serial"] = _mode(wall=4.0, n_threads=1, ck=1)
    ws.modes["parallel"] = _mode(wall=1.0, n_threads=4, ck=2)
    txt = format_summary_table([ws], modes=("parallel", "serial"))
    assert "DIVERGENT" in txt


def test_format_spec_listing_lists_workloads() -> None:
    specs = [_spec("alpha"), _spec("beta", num_threads=8)]
    txt = format_spec_listing(specs)
    assert "alpha" in txt and "beta" in txt
    assert "threads" in txt
