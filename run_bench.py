"""
General benchmark driver for the multithreaded Python workload suite.

For each selected workload:

  * import the module to read its `BENCH_SPEC` (name, description,
    num_threads, sync, work_units)
  * spawn `python workloads/<name>.py` N times per requested mode
    (serial, parallel, or both), with `BENCH_MODE` in the env
  * parse the single `BENCH_RESULT {...}` line each run emits and record
    wall time, CPU time, peak RSS, and the checksum
  * aggregate metrics across the N runs of each mode and, in `both`
    mode, compute speedup and parallel efficiency
"""

from __future__ import annotations

import argparse
import importlib
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import sysconfig
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent
WORKLOADS_DIR = ROOT / "workloads"

MODES = ("parallel", "serial")


###################
# MACHINE BANNER  #
###################


def _git_short_sha() -> str:
    """Return short HEAD SHA, or 'unknown' if git isn't available."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=5,
            check=False,
        )
    except FileNotFoundError, subprocess.TimeoutExpired:
        return "unknown"
    if proc.returncode != 0:
        return "unknown"
    return proc.stdout.strip() or "unknown"


def _free_threaded() -> bool:
    """Best-effort detection of a free-threaded CPython build."""
    if sysconfig.get_config_var("Py_GIL_DISABLED"):
        return True
    is_enabled = getattr(sys, "_is_gil_enabled", None)
    if callable(is_enabled):
        return not is_enabled()
    return False


def format_machine_info() -> str:
    """Multi-line banner: CPU, arch, cores+freq, RAM, OS, Python, commit SHA."""
    cores_str = "? cores"
    freq_str = ""
    ram_str = "? RAM"
    try:
        import psutil  # type: ignore[import-not-found]

        phys = psutil.cpu_count(logical=False) or 0
        logical = psutil.cpu_count(logical=True) or 0
        cores_str = f"{phys}P / {logical}L cores"
        # `.total` = max physical RAM installed (in bytes). Deliberately
        # NOT `.available` / `.free` — those fluctuate with load and we
        # want to report the machine's capacity, not its current state.
        ram_gb = psutil.virtual_memory().total / (1024**3)
        ram_str = f"{ram_gb:.1f} GB RAM"
        # `cpu_freq()` returns scpufreq(current, min, max) in MHz, or
        # None on platforms without cpufreq (some Linux containers).
        freq = psutil.cpu_freq()
        if freq is not None:
            mhz = freq.max or freq.current or 0
            if mhz:
                freq_str = f" @ {mhz / 1000:.2f} GHz"
    except Exception:
        pass

    cpu = platform.processor() or "unknown CPU"
    arch = platform.machine() or "unknown-arch"
    os_str = f"{platform.system()} {platform.release()} ({platform.version()})"
    py_str = (
        f"{platform.python_implementation()} {platform.python_version()} "
        f"(free-threaded: {'yes' if _free_threaded() else 'no'})"
    )

    return "\n".join(
        [
            f"Machine: {cpu}",
            f"Arch:    {arch} | {cores_str}{freq_str} | {ram_str}",
            f"OS:      {os_str}",
            f"Python:  {py_str}",
            f"Commit:  {_git_short_sha()}",
        ]
    )


##########
# models #
##########


@dataclass(frozen=True, slots=True)
class RunResult:
    workload: str
    mode: str
    run_index: int
    checksum: Optional[int]
    ok: bool
    wall_s: float = float("nan")
    cpu_s: float = float("nan")
    peak_mb: float = float("nan")
    subprocess_wall_s: float = 0.0
    stderr_tail: str = ""


@dataclass(frozen=True, slots=True)
class ModeStats:
    n_ok: int
    n_total: int
    checksum: Any
    checksum_stable: bool
    wall_mean: float = float("nan")
    wall_stdev: float = float("nan")
    wall_min: float = float("nan")
    cpu_mean: float = float("nan")
    peak_mb_mean: float = float("nan")
    cpu_efficiency: float = float(
        "nan"
    )  # cpu_mean / (wall_mean * num_threads)


@dataclass(frozen=True, slots=True)
class WorkloadStats:
    workload: str
    spec: dict[str, Any]
    modes: dict[str, ModeStats] = field(default_factory=dict)

    @property
    def speedup(self) -> float:
        s = self.modes.get("serial")
        p = self.modes.get("parallel")
        if s is None or p is None:
            return float("nan")
        if (
            not (math.isfinite(s.wall_mean) and math.isfinite(p.wall_mean))
            or p.wall_mean <= 0
        ):
            return float("nan")
        return s.wall_mean / p.wall_mean

    @property
    def parallel_efficiency(self) -> float:
        nt = int(self.spec.get("num_threads", 1))
        if nt < 1:
            return float("nan")
        sp = self.speedup
        if not math.isfinite(sp):
            return float("nan")
        return sp / nt

    @property
    def checksum_divergence(self) -> bool:
        s = self.modes.get("serial")
        p = self.modes.get("parallel")
        if s is None or p is None:
            return False
        if s.checksum is None or p.checksum is None:
            return False
        return s.checksum != p.checksum


#############
# DISCOVERY #
#############


def discover_workloads() -> list[str]:
    """
    Return sorted list of workload module names under `workloads/`.
    """
    names = []
    for p in sorted(WORKLOADS_DIR.glob("*.py")):
        if p.name in ("__init__.py", "common.py"):
            continue
        names.append(p.stem)
    return names


def load_spec(name: str) -> dict[str, Any]:
    """
    Import `workloads/<name>.py` and return its BENCH_SPEC.
    """
    if str(WORKLOADS_DIR) not in sys.path:
        sys.path.insert(0, str(WORKLOADS_DIR))

    mod = importlib.import_module(name)
    spec = getattr(mod, "BENCH_SPEC", None)
    if not isinstance(spec, dict):
        raise ValueError(f"workload {name!r} is missing a BENCH_SPEC dict")

    required = {"name", "description", "num_threads", "sync", "work_units"}
    missing = required - set(spec)
    if missing:
        raise ValueError(
            f"workload {name!r} BENCH_SPEC missing fields: {sorted(missing)}"
        )
    return spec


##########
# RUNNER #
##########


def parse_bench_result(stdout: str) -> dict[str, Any]:
    """
    Return the JSON payload of the last BENCH_RESULT line in stdout.
    """
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if line.startswith("BENCH_RESULT "):
            try:
                return json.loads(line[len("BENCH_RESULT ") :])
            except json.JSONDecodeError as e:
                raise ValueError(f"malformed BENCH_RESULT JSON: {e}") from e
    raise ValueError("no BENCH_RESULT line in workload output")


def run_one(
    workload: str, mode: str, run_index: int, smoke: bool, timeout_s: float
) -> RunResult:
    env = os.environ.copy()
    if smoke:
        env["BENCH_SMOKE"] = "1"
    env["BENCH_MODE"] = mode
    env["PYTHONIOENCODING"] = "utf-8"
    cmd = [sys.executable, str(WORKLOADS_DIR / f"{workload}.py")]
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
            env=env,
        )
    except subprocess.TimeoutExpired as e:
        wall = time.perf_counter() - t0
        return RunResult(
            workload=workload,
            mode=mode,
            run_index=run_index,
            checksum=None,
            ok=False,
            subprocess_wall_s=wall,
            stderr_tail=f"TIMEOUT after {timeout_s:.0f}s: {e}",
        )

    # successful run
    wall = time.perf_counter() - t0
    if proc.returncode != 0:
        return RunResult(
            workload=workload,
            mode=mode,
            run_index=run_index,
            checksum=None,
            ok=False,
            subprocess_wall_s=wall,
            stderr_tail=(proc.stderr or "")[-400:],
        )

    try:
        payload = parse_bench_result(proc.stdout)
    except ValueError as e:
        return RunResult(
            workload=workload,
            mode=mode,
            run_index=run_index,
            checksum=None,
            ok=False,
            subprocess_wall_s=wall,
            stderr_tail=f"{e}; stderr tail: {(proc.stderr or '')[-200:]}",
        )
    return RunResult(
        workload=workload,
        mode=mode,
        run_index=run_index,
        wall_s=float(payload["time_s"]),
        cpu_s=float(payload.get("cpu_s", float("nan"))),
        peak_mb=float(payload["peak_mb"]),
        checksum=payload.get("checksum"),
        ok=True,
        subprocess_wall_s=wall,
    )


#############
# AGGREGATE #
#############


def aggregate_mode(runs: list[RunResult], num_threads: int) -> ModeStats:
    ok = [r for r in runs if r.ok]
    n_total = len(runs)
    if not ok:
        return ModeStats(
            n_ok=0, n_total=n_total, checksum=None, checksum_stable=True
        )
    walls = [r.wall_s for r in ok]
    cpus = [r.cpu_s for r in ok if math.isfinite(r.cpu_s)]
    peaks = [r.peak_mb for r in ok]
    checksums = [r.checksum for r in ok]
    wall_mean = statistics.fmean(walls)
    cpu_mean = statistics.fmean(cpus) if cpus else float("nan")
    nt = max(1, int(num_threads))
    cpu_eff = (
        (cpu_mean / (wall_mean * nt))
        if (math.isfinite(cpu_mean) and wall_mean > 0)
        else float("nan")
    )
    return ModeStats(
        n_ok=len(ok),
        n_total=n_total,
        wall_mean=wall_mean,
        wall_stdev=statistics.stdev(walls) if len(walls) > 1 else 0.0,
        wall_min=min(walls),
        cpu_mean=cpu_mean,
        peak_mb_mean=statistics.fmean(peaks),
        cpu_efficiency=cpu_eff,
        checksum=checksums[0],
        checksum_stable=all(c == checksums[0] for c in checksums),
    )


##########
# OUTPUT #
##########


def format_spec_listing(specs: list[dict[str, Any]]) -> str:
    name_w = max((len(s["name"]) for s in specs), default=8)
    sync_w = max((len(str(s["sync"])) for s in specs), default=4)
    out = []
    header = f"{'workload'.ljust(name_w)}  threads  {'sync'.ljust(sync_w)}  work_units  description"
    out.append(header)
    out.append("-" * len(header))
    for s in specs:
        out.append(
            f"{s['name'].ljust(name_w)}  "
            f"{int(s['num_threads']):>7}  "
            f"{str(s['sync']).ljust(sync_w)}  "
            f"{int(s['work_units']):>10}  "
            f"{s['description']}"
        )
    return "\n".join(out)


def _fnum(x: float, p: int = 3) -> str:
    return "-" if not math.isfinite(x) else f"{x:.{p}f}"


def _fpct(x: float) -> str:
    return "-" if not math.isfinite(x) else f"{x * 100:.1f}%"


def _checksum_cell(stats: ModeStats) -> str:
    if stats.checksum is None:
        return "-"
    base = str(stats.checksum)
    return base if stats.checksum_stable else base + "*"


def _render_table(cols: list[str], rows: list[list[str]]) -> str:
    widths = [
        max(len(r[i]) for r in (rows + [cols])) for i in range(len(cols))
    ]
    lines = []
    lines.append("  ".join(c.ljust(widths[i]) for i, c in enumerate(cols)))
    lines.append("  ".join("-" * widths[i] for i in range(len(cols))))
    for r in rows:
        lines.append(
            "  ".join(r[i].ljust(widths[i]) for i in range(len(cols)))
        )
    return "\n".join(lines)


def format_summary_table(
    stats_list: list[WorkloadStats], modes: tuple[str, ...]
) -> str:
    """Pick columns based on which modes were run."""
    rows: list[list[str]] = []
    has_serial = "serial" in modes
    has_parallel = "parallel" in modes
    both = has_serial and has_parallel

    if both:
        cols = [
            "workload",
            "runs",
            "threads",
            "serial wall (s)",
            "parallel wall (s)",
            "± stdev",
            "speedup",
            "par eff",
            "peak MB",
            "checksum",
        ]
    elif has_parallel:
        cols = [
            "workload",
            "runs",
            "threads",
            "wall mean (s)",
            "± stdev",
            "wall min (s)",
            "cpu mean (s)",
            "cpu eff",
            "peak MB",
            "checksum",
        ]
    else:  # serial only
        cols = [
            "workload",
            "runs",
            "wall mean (s)",
            "± stdev",
            "wall min (s)",
            "peak MB",
            "checksum",
        ]

    for ws in sorted(stats_list, key=lambda r: r.workload):
        if both:
            s = ws.modes["serial"]
            p = ws.modes["parallel"]
            runs_cell = f"{p.n_ok}/{p.n_total}"
            ck = (
                _checksum_cell(p)
                if p.checksum is not None
                else _checksum_cell(s)
            )
            if ws.checksum_divergence:
                ck += " DIVERGENT"
            rows.append(
                [
                    ws.workload,
                    runs_cell,
                    str(int(ws.spec.get("num_threads", 0))),
                    _fnum(s.wall_mean),
                    _fnum(p.wall_mean),
                    _fnum(p.wall_stdev),
                    _fnum(ws.speedup, 2) + "x",
                    _fpct(ws.parallel_efficiency),
                    _fnum(p.peak_mb_mean, 1),
                    ck,
                ]
            )
        elif has_parallel:
            p = ws.modes["parallel"]
            rows.append(
                [
                    ws.workload,
                    f"{p.n_ok}/{p.n_total}",
                    str(int(ws.spec.get("num_threads", 0))),
                    _fnum(p.wall_mean),
                    _fnum(p.wall_stdev),
                    _fnum(p.wall_min),
                    _fnum(p.cpu_mean),
                    _fpct(p.cpu_efficiency),
                    _fnum(p.peak_mb_mean, 1),
                    _checksum_cell(p),
                ]
            )
        else:
            s = ws.modes["serial"]
            rows.append(
                [
                    ws.workload,
                    f"{s.n_ok}/{s.n_total}",
                    _fnum(s.wall_mean),
                    _fnum(s.wall_stdev),
                    _fnum(s.wall_min),
                    _fnum(s.peak_mb_mean, 1),
                    _checksum_cell(s),
                ]
            )
    return _render_table(cols, rows)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Run multithreaded Python benchmarks and print results to stdout."
    )
    p.add_argument(
        "--runs",
        type=int,
        default=5,
        help="runs per (workload, mode) cell (default 5)",
    )
    p.add_argument(
        "--benchmarks",
        default="",
        help="comma-separated subset of workload names (default: all)",
    )
    p.add_argument(
        "--mode",
        choices=("parallel", "serial", "both"),
        default="both",
        help="which mode to run; with 'both' the table includes speedup (default: both)",
    )
    p.add_argument(
        "--smoke",
        action="store_true",
        help="set BENCH_SMOKE=1 in workloads (small problem sizes)",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=600.0,
        help="per-subprocess timeout in seconds (default 600)",
    )
    p.add_argument(
        "--list",
        action="store_true",
        help="list discovered workloads with their BENCH_SPEC and exit",
    )
    p.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="print one line per run as it completes",
    )
    args = p.parse_args(argv)

    all_w = discover_workloads()
    if args.benchmarks.strip():
        wanted = [w.strip() for w in args.benchmarks.split(",") if w.strip()]
        unknown = [w for w in wanted if w not in all_w]
        if unknown:
            p.error(f"unknown benchmark(s): {unknown}; have: {all_w}")
        workloads = wanted
    else:
        workloads = all_w

    try:
        specs = [load_spec(w) for w in workloads]
    except (ImportError, ValueError) as e:
        print(f"error loading workload spec: {e}", file=sys.stderr)
        return 2

    if args.list:
        print(format_spec_listing(specs))
        return 0

    if args.runs < 1:
        p.error("--runs must be >= 1")

    modes: tuple[str, ...] = MODES if args.mode == "both" else (args.mode,)
    total = len(workloads) * args.runs * len(modes)
    print(format_machine_info())
    print()
    print(
        f"Running {len(workloads)} workload(s) × {args.runs} run(s) × "
        f"{len(modes)} mode(s) ({','.join(modes)}) = {total} subprocess(es); "
        f"smoke={args.smoke}"
    )
    print()

    stats_list: list[WorkloadStats] = []
    done = 0
    for w, spec in zip(workloads, specs, strict=True):
        ws = WorkloadStats(workload=w, spec=spec)
        for mode in modes:
            runs: list[RunResult] = []
            for i in range(args.runs):
                r = run_one(
                    w, mode, i, smoke=args.smoke, timeout_s=args.timeout
                )
                runs.append(r)
                done += 1
                if args.verbose:
                    if r.ok:
                        print(
                            f"  [{done:>3}/{total}] {w:<22} {mode:<8} run {i + 1}/{args.runs}  "
                            f"ok  wall={r.wall_s:7.3f}s  cpu={r.cpu_s:7.3f}s  "
                            f"peak={r.peak_mb:6.1f}MB"
                        )
                    else:
                        print(
                            f"  [{done:>3}/{total}] {w:<22} {mode:<8} run {i + 1}/{args.runs}  "
                            f"FAIL  subprocess_wall={r.subprocess_wall_s:6.1f}s"
                        )
                        print(f"     ! {r.stderr_tail.strip()[:200]}")
            ws.modes[mode] = aggregate_mode(
                runs, int(spec.get("num_threads", 1))
            )
        stats_list.append(ws)
        if not args.verbose:
            _print_workload_oneliner(ws, modes)

    print()
    print("=" * 70)
    print(format_summary_table(stats_list, modes))
    print("=" * 70)
    if "both" == args.mode:
        print("\nspeedup = serial_wall_mean / parallel_wall_mean")
        print("\npar eff = speedup / num_threads")
        print(
            "'*' on checksum = unstable across runs;  "
            "'DIVERGENT' = serial and parallel disagree."
        )
    elif args.mode == "parallel":
        print(
            "\ncpu eff = mean_cpu_time / (mean_wall_time * num_threads); "
            "1.0 = perfect parallel use."
        )

    any_fail = any(
        ms.n_ok < ms.n_total for ws in stats_list for ms in ws.modes.values()
    )
    any_unstable = any(
        not ms.checksum_stable for ws in stats_list for ms in ws.modes.values()
    )
    any_divergent = any(ws.checksum_divergence for ws in stats_list)
    return 1 if (any_fail or any_unstable or any_divergent) else 0


def _print_workload_oneliner(
    ws: WorkloadStats, modes: tuple[str, ...]
) -> None:
    parts = [f"  {ws.workload:<22}"]
    failed = False
    for m in modes:
        ms = ws.modes[m]
        if ms.n_ok == 0:
            parts.append(f"{m}=FAIL")
            failed = True
        else:
            parts.append(f"{m} wall={ms.wall_mean:6.3f}s")
    if "serial" in modes and "parallel" in modes and not failed:
        parts.append(
            f"speedup={ws.speedup:5.2f}x  par_eff={ws.parallel_efficiency * 100:5.1f}%"
        )
    if ws.checksum_divergence:
        parts.append("CHECKSUM DIVERGENCE")
    print("  ".join(parts))


if __name__ == "__main__":
    sys.exit(main())
