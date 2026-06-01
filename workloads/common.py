"""
Shared helpers for every workload script.

A workload is a standalone Python script the driver can run as
`python <workload>.py`. Each workload:

  * imports this module
  * defines `main_parallel()` (multithreaded) and `main_serial()`
    (single-thread baseline) — both return the same integer checksum
    for the same input
  * ends with `common.run_entry(main_parallel, main_serial)`, which
    picks one based on the `BENCH_MODE` env var (`parallel` by default,
    `serial` for the baseline run) and emits the single
    `BENCH_RESULT {...}` line the driver parses out of stdout.

Workloads honor `BENCH_SMOKE=1` (set by `--smoke` and by the test
suite) to scale problem sizes down ~10x.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from collections.abc import Callable, Iterable, Sequence
from typing import TypeVar

NUM_THREADS = 8
SEMAPHORE_COUNT = max(1, NUM_THREADS // 2)

T = TypeVar("T")
R = TypeVar("R")


def smoke() -> bool:
    return os.environ.get("BENCH_SMOKE") == "1"


def scaled(full: int, smoke_value: int) -> int:
    """Pick `smoke_value` when BENCH_SMOKE=1, else `full`."""
    return smoke_value if smoke() else full


def time_main(main_fn: Callable[[], object]) -> tuple[float, float, object]:
    """
    Time `main_fn()`. Returns (wall_seconds, cpu_seconds, return_value).

    `cpu_seconds` is `time.process_time()` deltas, which sums user+system
    CPU time across all threads of the process.
    """
    w0 = time.perf_counter()
    c0 = time.process_time()
    checksum = main_fn()
    c1 = time.process_time()
    w1 = time.perf_counter()
    return (w1 - w0, c1 - c0, checksum)


def _peak_rss_mb() -> float:
    """
    Peak resident set in MB.

    Windows: `psutil.Process().memory_info().peak_wset` (bytes, lifetime peak).
    POSIX:   `resource.getrusage(RUSAGE_SELF).ru_maxrss` (kB on Linux, B on Mac).
    """
    if sys.platform == "win32":
        try:
            import psutil  # type: ignore[import-not-found]

            return psutil.Process().memory_info().peak_wset / (1024 * 1024)
        except Exception:
            return 0.0
    try:
        import resource  # type: ignore[import-not-found]

        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # Linux: kB. macOS: bytes.
        if sys.platform == "darwin":
            return rss / (1024 * 1024)
        return rss / 1024
    except Exception:
        return 0.0


def report_result(time_s: float, cpu_s: float, checksum: object) -> None:
    """
    Print one BENCH_RESULT line. The driver reads only this line.
    """
    payload = {
        "time_s": float(time_s),
        "cpu_s": float(cpu_s),
        "peak_mb": float(_peak_rss_mb()),
        "checksum": checksum,
    }
    sys.stdout.write("BENCH_RESULT " + json.dumps(payload) + "\n")
    sys.stdout.flush()


def run_entry(
    main_parallel: Callable[[], object], main_serial: Callable[[], object]
) -> None:
    """
    Standard workload entry point. Picks parallel or serial from BENCH_MODE.

    `BENCH_MODE=serial` runs the single-threaded baseline; anything else
    (default `parallel`) runs the multithreaded version.
    """
    mode = os.environ.get("BENCH_MODE", "parallel")
    fn = main_serial if mode == "serial" else main_parallel
    t, c, ck = time_main(fn)
    report_result(t, c, ck)


def parallel_for(
    fn: Callable[[int, T], R],
    items: Sequence[T],
    num_threads: int = NUM_THREADS,
) -> list[R]:
    """
    Run `fn(thread_id, item)` for each item across `num_threads` workers.

    Each thread takes one slice of `items`. Returns results in input order.
    """
    n = len(items)
    results: list[R] = [None] * n  # type: ignore[list-item]
    used_tids: set[int] = set()
    used_lock = threading.Lock()

    def worker(tid: int, start: int, stop: int) -> None:
        with used_lock:
            used_tids.add(tid)
        for i in range(start, stop):
            results[i] = fn(tid, items[i])

    threads = []
    chunk = (n + num_threads - 1) // num_threads
    for tid in range(num_threads):
        start = tid * chunk
        stop = min(start + chunk, n)
        if start >= stop:
            continue
        t = threading.Thread(target=worker, args=(tid, start, stop))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    assert_threads_used(used_tids, n=min(num_threads, n))
    return results


def barrier_workers(
    target: Callable[..., None],
    num_threads: int = NUM_THREADS,
    extra_args: Iterable[object] = (),
) -> None:
    """
    Start `num_threads` workers; each gets (tid, barrier, *extra_args).
    """
    barrier = threading.Barrier(num_threads)
    threads = []
    for tid in range(num_threads):
        t = threading.Thread(target=target, args=(tid, barrier, *extra_args))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()


def assert_threads_used(tids: Iterable[int], n: int) -> None:
    """
    Sanity: the work touched at least `n` distinct thread ids.
    """
    s = set(tids)
    if len(s) < n:
        raise AssertionError(
            f"expected {n} distinct worker tids, saw {len(s)}: {sorted(s)}"
        )
