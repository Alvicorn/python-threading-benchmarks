# Benchmark reports

This directory collects benchmark results contributed from different
machines so the suite's free-threadedPython speedup numbers can be
compared across CPU architectures, OS, and Python builds.

## The standard run

Every report must be produced with **the exact same command and
configuration** so the numbers are comparable:

```sh
uv run --python <python-version> python run_bench.py --runs 10 --mode both
```

- **Worker threads:** `common.NUM_THREADS = 8`.
- **Problem sizes:** full size (no `--smoke`). Smoke mode is for fast
  development feedback, not for reporting.
- **Modes:** `both` — each workload runs serial and parallel so the
  driver can compute `speedup = serial_wall_mean / parallel_wall_mean`.
- **Runs per cell:** 10.
- **Python:** any CPython 3.13+, free-threaded or GIL'd. The
  exact build you used is captured automatically in the report. The
  suite is designed for free-threaded; on a GIL'd build expect
  speedups around 1×.

## How the `benchmarks` branch works

Reports are run against the tip of a long-lived **`benchmarks`** branch,
not against `main`. The `benchmarks` branch advances only when the
maintainer deliberately fast-forwards it to a chosen `main` commit
(after a new workload, tuned constants, regenerated goldens, etc.).
Between bumps every report quotes the same commit SHA, so cross-machine
numbers are directly comparable.

[`run_report.py`](run_report.py) refuses to run if your HEAD isn't at
the tip of `benchmarks`. Past reports under this directory stay as the
historical record of older snapshots — their commit SHAs identify which
snapshot they were measured against.

## How to contribute a report

In this example we will use `3.14+freethreaded` as the python version.

1. `git fetch origin`
2. `git switch benchmarks`
3. `uv sync --python 3.14+freethreaded && uv run --python 3.14+freethreaded pytest tests/ -q`
   — confirm a green baseline on your machine before benchmarking.
   Make sure the interpreter you want to benchmark is also installed
   (`uv python install 3.14+freethreaded` or whichever version you
   choose).
4. `git switch -c benchmarks-<good-branch-name>`. Pick a name that identifies your machine
    + Python build. If you can't decide, the auto-generated report directory (see step 5) 
    makes a fine fallback. Examples:
   `benchmarks-amd-8c16t-py3.14ft`,
   `benchmarks-intel-12c-py3.13`,
   `benchmarks-44c6f37-amd64-windows-amd-8c16t-3.2ghz-27gb-py3.14ft`. 
5. Generate the report. The required `--python` flag picks which interpreter is measured.
   The outer `--python` only controls which Python runs the report script itself:

   ```sh
   uv run --python 3.14+freethreaded python reports/run_report.py \
       --python 3.14+freethreaded
   ```

   The script auto-creates a directory whose name describes both the
   benchmark snapshot and the machine being benchmarked, e.g.

   `reports/44c6f37-amd64-windows-amd-8c16t-3.2ghz-27gb-py3.14ft/README.md`

   Segments, in order:

   | Segment | Meaning |
   |---|---|
   | `44c6f37` | short SHA of the `benchmarks` branch tip |
   | `amd64` | CPU instruction set (`platform.machine()`) |
   | `windows` | OS (`platform.system()`) |
   | `amd` | CPU vendor (`amd` / `intel` / `apple` / `arm`) |
   | `8c16t` | 8 physical / 16 logical cores |
   | `3.2ghz` | max CPU clock (omitted if `psutil` can't report it) |
   | `27gb` | total physical RAM, rounded |
   | `py3.14ft` | the `--python` flag — `py3.14ft` is 3.14 free-threaded, `py3.13` is 3.13 GIL'd, `py-custom` for anything else |

   Re-running on the same machine with the same Python overwrites the
   same directory. A different CPU vendor / core count / RAM / Python
   build produces a fresh directory. GitHub renders the `README.md`
   automatically when you navigate to the directory.
6. Sanity-check the new `reports/<dir>/README.md`: machine block
   (CPU, frequency, RAM, OS, Python build) and the speedup table.
7. Edit this file (`reports/README.md`) to add one row to the
   **Index of submitted reports** table for your machine.
8. `git add reports/<new-directory>/ reports/README.md && git commit -m "report: <short machine label>"`
9. `git push -u origin benchmarks-<good-branch-name>` and open a PR
   from that branch into `main`. CI runs the test suite against
   `3.14+freethreaded`; once green and reviewed, a maintainer merges.
   **Do not push directly to `main` or `benchmarks`** — those are
   maintained only via merged PRs.

The helper script captures:

- CPU model + architecture, physical/logical core counts, max clock
  frequency, total physical RAM
- OS + version
- Python implementation, version, and whether the build is free-threaded
- The `benchmarks`-branch commit SHA at run time
- The full `run_bench.py` stdout (verbatim, in a collapsible section)
- A reformatted speedup table with one row per workload

## Index of submitted reports

| Report | CPU | OS | Python | Commit | Geomean speedup |
|---|---|---|---|---|---|
| _No reports submitted yet — be the first!_ | | | | | |
