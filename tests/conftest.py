"""Shared pytest helpers for the benchmark test suite."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKLOADS_DIR = ROOT / "workloads"

WORKLOADS = sorted(
    p.stem
    for p in WORKLOADS_DIR.glob("*.py")
    if p.name not in ("__init__.py", "common.py")
)


def run_workload(
    name: str, *, mode: str = "parallel", smoke: bool = True, timeout: int = 90
) -> subprocess.CompletedProcess:
    """Spawn `python workloads/<name>.py` as a subprocess.

    `mode` is passed via the BENCH_MODE env var ('parallel' or 'serial').
    """
    script = str(WORKLOADS_DIR / f"{name}.py")
    cmd = [sys.executable, script]
    env = os.environ.copy()
    if smoke:
        env["BENCH_SMOKE"] = "1"
    env["BENCH_MODE"] = mode
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=env,
    )


def parse_bench_result(stdout: str) -> dict:
    import json

    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if line.startswith("BENCH_RESULT "):
            return json.loads(line[len("BENCH_RESULT ") :])
    raise AssertionError(
        "no BENCH_RESULT line in stdout:\n" + (stdout[-1000:] or "<empty>")
    )
