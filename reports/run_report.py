"""
Run the benchmark suite against the `benchmarks` branch and emit a
markdown report suitable for committing under ``reports/``.

Usage:
    uv sync --python 3.14+freethreaded
    uv run --python 3.14+freethreaded pytest tests/ -q       # baseline
    git switch -c benchmarks-<good-branch-name>              # feature branch
    uv run --python 3.14+freethreaded python reports/run_report.py \
           --python 3.14+freethreaded
    # reports/<sha>-<arch>-<os>-<vendor>-<cores>-[freq-]<ram>-<py-tag>/README.md

The outer `--python` selects the interpreter that runs THIS script.
The inner `--python` (required) selects the interpreter the benchmark
is measured against — they can differ when you want to compare builds.

The `benchmarks` branch holds the stable benchmark code that all
reports run against, so every report for the same benchmark snapshot
quotes the same commit SHA. The feature branch is created *off
`benchmarks`* so HEAD still matches the tip of `benchmarks` when the
script runs. The script refuses to run if HEAD is not at the tip of
`benchmarks`, and refuses to run if the target Python interpreter is
not already installed.
"""

from __future__ import annotations

import argparse
import datetime
import math
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from run_bench import discover_workloads, load_spec  # noqa: E402


def _git_rev_parse(ref: str) -> str | None:
    proc = subprocess.run(
        ["git", "rev-parse", "--short", ref],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    if proc.returncode != 0:
        return None
    out = proc.stdout.strip()
    return out or None


def resolve_benchmarks_sha() -> str | None:
    """
    Return the short SHA of `benchmarks` (local first, then origin).
    """
    return _git_rev_parse("benchmarks") or _git_rev_parse("origin/benchmarks")


def gate_on_benchmarks_branch() -> str:
    """
    Verify HEAD matches the tip of the `benchmarks` branch. Returns
    the short SHA of `benchmarks` on success; exits otherwise.
    """
    bench = resolve_benchmarks_sha()
    if bench is None:
        sys.stderr.write(
            "Could not resolve `benchmarks` ref (neither local nor "
            "origin/benchmarks).\nRun `git fetch` and try again.\n"
        )
        raise SystemExit(2)

    head = _git_rev_parse("HEAD") or "unknown"
    if head != bench:
        sys.stderr.write(
            "This report must be run against the `benchmarks` branch.\n"
            f"  benchmarks: {bench}\n"
            f"  HEAD:       {head}\n\n"
            "Run:\n"
            "  git fetch origin\n"
            "  git switch benchmarks\n"
            "  uv sync --python 3.14+freethreaded\n"
            "  git switch -c benchmarks-<good-branch-name>\n"
            "  uv run --python 3.14+freethreaded python reports/run_report.py \\\n"
            "      --python 3.14+freethreaded\n"
            "Then commit the new report directory + an index row and open a "
            "PR from `benchmarks-<good-branch-name>` into `main`.\n"
        )
        raise SystemExit(2)
    return bench


def verify_python_installed(spec: str) -> str:
    """
    Confirm `uv` can resolve `spec` to an installed interpreter.

    Returns the absolute path to that interpreter on success.
    Exits non-zero otherwise.
    """
    try:
        proc = subprocess.run(
            ["uv", "python", "find", spec],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        sys.stderr.write(
            "error: `uv` is not on PATH. Install uv first:\n"
            "  https://docs.astral.sh/uv/getting-started/installation/\n"
        )
        raise SystemExit(2) from None

    if proc.returncode != 0:
        sys.stderr.write(
            f'error: Python "{spec}" is not installed on this machine.\n\n'
            f"uv could not find an interpreter matching `{spec}`. "
            "Install it with:\n"
            f"  uv python install {spec}\n\n"
            "Then re-run:\n"
            f"  uv run --python 3.14+freethreaded python "
            f"reports/run_report.py --python {spec}\n"
        )
        if proc.stderr.strip():
            sys.stderr.write(f"\n(uv said: {proc.stderr.strip()})\n")
        raise SystemExit(2)
    return proc.stdout.strip()


def extract_machine_block(stdout: str) -> str:
    """
    Pull the leading machine banner from driver stdout.

    `run_bench.py` prints `format_machine_info()` first, then a blank
    line. The banner ends at `Commit:` (5 lines) or at the first
    blank line, whichever comes first.
    """
    block: list[str] = []
    for line in stdout.splitlines():
        if not line.strip():
            break
        block.append(line)
        if line.startswith("Commit:"):
            break
    return "\n".join(block)


def parse_summary_rows(stdout: str) -> list[dict[str, str]]:
    """
    Extract workload rows from the driver's `--mode both` summary table.
    """
    lines = stdout.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip().startswith("workload") and "speedup" in line:
            start = i
            break
    if start is None:
        raise ValueError("could not find summary table in driver stdout")

    rows: list[dict[str, str]] = []
    # start+1 is the dashes row; data starts at start+2.
    for line in lines[start + 2 :]:
        if line.startswith("=") or not line.strip():
            break
        fields = re.split(r"\s{2,}", line.strip())
        # both-mode columns: workload, runs, threads, serial wall,
        # parallel wall, stdev, speedup, par eff, peak MB, checksum.
        if len(fields) < 7:
            continue
        rows.append(
            {
                "workload": fields[0],
                "serial_s": fields[3],
                "parallel_s": fields[4],
                "speedup": fields[6],  # e.g. "4.13x"
            }
        )
    return rows


def geomean_speedup(rows: list[dict[str, str]]) -> float:
    """
    Geometric mean of the speedup column; skips non-finite entries.
    """
    log_vals: list[float] = []
    for r in rows:
        try:
            val = float(r["speedup"].rstrip("x"))
        except ValueError:
            continue
        if math.isfinite(val) and val > 0:
            log_vals.append(math.log(val))
    if not log_vals:
        return float("nan")
    return math.exp(sum(log_vals) / len(log_vals))


def _machine_field(machine: str, prefix: str) -> str:
    for line in machine.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return "unknown"


_VENDOR_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("amd", re.compile(r"AuthenticAMD|\bAMD\b", re.I)),
    ("intel", re.compile(r"GenuineIntel|\bIntel\b", re.I)),
    ("apple", re.compile(r"\bApple\b", re.I)),
    ("arm", re.compile(r"\bARM\b|aarch64", re.I)),
]


def _cpu_vendor() -> str:
    """
    Map `platform.processor()` to a short vendor tag for the dirname.
    """
    raw = platform.processor() or ""
    for tag, pat in _VENDOR_PATTERNS:
        if pat.search(raw):
            return tag
    return "unkcpu"


def _python_tag(spec: str) -> str:
    """
    Use the `--python SPEC` exactly as the user passed it on the CLI.

    The only transformation is filesystem-safety: path separators are
    swapped for `_` so a spec like `/usr/bin/python3.13` doesn't end up
    creating nested directories. Everything else (including the `+` in
    `3.14+freethreaded`) is preserved as-is.
    """
    return spec.replace("/", "_").replace("\\", "_")


def auto_dirname(bench_sha: str, python_spec: str) -> str:
    """
    Build a readable, machine-distinguishing report directory name.

    Shape: `<bench-sha>-<arch>-<os>-<vendor>-<cores>-[freq-]<ram>-<py-tag>`,
    e.g. `44c6f37-amd64-windows-amd-8c16t-3.2ghz-27gb-py3.14ft`.

    Same machine + same Python -> same dirname (so a re-run cleanly
    overwrites the previous report). Different CPU vendor / cores /
    freq / RAM / Python build -> different dirname.
    """
    arch = (platform.machine() or "unkarch").lower()
    osys = (platform.system() or "unkos").lower()
    vendor = _cpu_vendor()

    cores = "?c?t"
    freq = ""
    ram = "?gb"
    try:
        import psutil  # type: ignore[import-not-found]

        phys = psutil.cpu_count(logical=False) or 0
        logi = psutil.cpu_count(logical=True) or 0
        cores = f"{phys}c{logi}t"
        ram_gb = round(psutil.virtual_memory().total / (1024**3))
        ram = f"{ram_gb}gb"
        cf = psutil.cpu_freq()
        if cf is not None:
            mhz = cf.max or cf.current or 0
            if mhz:
                freq = f"{mhz / 1000:.1f}ghz"
    except Exception:
        pass

    py = _python_tag(python_spec)
    segments = [bench_sha, arch, osys, vendor, cores]
    if freq:
        segments.append(freq)
    segments.extend([ram, py])
    return "-".join(segments)


def build_report(stdout: str, bench_sha: str, python_spec: str) -> str:
    machine = extract_machine_block(stdout)
    rows = parse_summary_rows(stdout)
    sync_by_workload = {
        w: str(load_spec(w)["sync"]) for w in discover_workloads()
    }
    for r in rows:
        r["sync"] = sync_by_workload.get(r["workload"], "?")

    gmean = geomean_speedup(rows)
    today = datetime.date.today().isoformat()
    cpu_full = _machine_field(machine, "Machine:")
    cpu_short = cpu_full.split(",")[0][:60]

    out: list[str] = []
    out.append(f"# Benchmark Report — {cpu_short}")
    out.append("")
    out.append(f"- **Date:** {today}")
    out.append(f"- **Benchmark commit:** `{bench_sha}` (tip of `benchmarks`)")
    out.append(f"- **Geomean speedup:** {gmean:.2f}×")
    out.append("")
    out.append("## Machine")
    out.append("")
    out.append("```")
    out.append(machine)
    out.append("```")
    out.append("")
    out.append("## Command")
    out.append("")
    out.append("```sh")
    out.append(
        f"uv run --python {python_spec} python run_bench.py "
        "--runs 10 --mode both"
    )
    out.append("```")
    out.append("")
    out.append("## Results")
    out.append("")
    out.append("| Workload | Sync | Serial (s) | Parallel (s) | Speedup |")
    out.append("|---|---|---:|---:|---:|")
    for r in rows:
        out.append(
            f"| `{r['workload']}` | {r['sync']} | "
            f"{r['serial_s']} | {r['parallel_s']} | {r['speedup']} |"
        )
    out.append("")
    out.append("## Raw output")
    out.append("")
    out.append("<details>")
    out.append("<summary>Full <code>run_bench.py</code> stdout</summary>")
    out.append("")
    out.append("```")
    out.append(stdout.rstrip())
    out.append("```")
    out.append("")
    out.append("</details>")
    out.append("")
    return "\n".join(out)


def _resolve_output_path(arg: str, bench_sha: str) -> Path | None:
    """
    Translate the --output argument into a concrete file path.

    Returns None for stdout. A directory-like argument (or the default)
    becomes `<dir>/README.md`.
    """
    if arg == "-":
        return None
    p = Path(arg)
    # If the user passed a directory, or a path with no .md suffix, treat
    # it as a directory and append README.md.
    if p.suffix.lower() != ".md":
        p = p / "README.md"
    return p


def main() -> int:
    p = argparse.ArgumentParser(
        description=(
            "Run the benchmark on the `benchmarks` branch and produce a "
            "markdown report. Must be invoked with HEAD at the tip of "
            "the `benchmarks` ref."
        )
    )
    p.add_argument(
        "--python",
        required=True,
        metavar="SPEC",
        help=(
            "Python interpreter to benchmark (e.g. '3.14+freethreaded', "
            "'3.14', '3.13', or a full path). REQUIRED. Must already be "
            "installed; the script does NOT auto-install."
        ),
    )
    p.add_argument(
        "--benchmarks",
        default="",
        help="Comma-separated subset (handy for a quick verify); default: all.",
    )
    p.add_argument(
        "-o",
        "--output",
        default="",
        help=(
            "Output path: '-' for stdout, a directory for "
            "<dir>/README.md, or an explicit .md path. Defaults to "
            "reports/<bench-sha>-<arch>-<os>-<vendor>-<cores>-"
            "[freq-]<ram>-<py-spec>/README.md (see reports/README.md "
            "for the segment legend)."
        ),
    )
    args = p.parse_args()

    bench_sha = gate_on_benchmarks_branch()
    interp_path = verify_python_installed(args.python)
    sys.stderr.write(f"Benchmarking Python `{args.python}` at {interp_path}\n")

    cmd = [
        "uv",
        "run",
        "--python",
        args.python,
        "python",
        str(ROOT / "run_bench.py"),
        "--runs",
        "10",
        "--mode",
        "both",
    ]
    if args.benchmarks:
        cmd += ["--benchmarks", args.benchmarks]

    sys.stderr.write(f"Running: {' '.join(cmd)}\n")
    sys.stderr.write("----\n")

    # Force the subprocess to emit UTF-8 so the driver's `×` chars round-trip
    # cleanly on Windows (default code page is cp1252).
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    # Stream stdout line-by-line so the contributor sees per-workload progress,
    # while also capturing the full text for `build_report()` to parse.
    captured: list[str] = []
    proc = subprocess.Popen(  # noqa: S603
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        bufsize=1,  # line-buffered
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        sys.stderr.write(line)
        sys.stderr.flush()
        captured.append(line)
    return_code = proc.wait()
    err_tail = (proc.stderr.read() if proc.stderr else "") or ""

    sys.stderr.write("----\n")

    if return_code != 0:
        sys.stderr.write(err_tail)
        return return_code

    full_stdout = "".join(captured)
    report = build_report(full_stdout, bench_sha, args.python)

    # Default output path: reports/<auto-dirname>/README.md
    default_dir = ROOT / "reports" / auto_dirname(bench_sha, args.python)
    out_path = (
        _resolve_output_path(args.output, bench_sha)
        if args.output
        else default_dir / "README.md"
    )
    if out_path is None:
        # stdout
        print(report)
    else:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")
        sys.stderr.write(f"Wrote report to {out_path}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
