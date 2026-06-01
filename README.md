# Python Threading Benchmarks

A focused collection of multi-threaded Python benchmarks designed to
characterize free-threaded Python (no-GIL) performance. 24 workloads
covering every `threading` synchronization primitive: Lock, RLock,
Event, Condition, Semaphore, BoundedSemaphore, Barrier, plus
`queue.Queue` / `queue.PriorityQueue`
(layered on Condition + Lock).

Each workload runs in both **parallel** and **same-total-work serial**
mode; the driver reports `speedup = serial / parallel`.

## Layout

```
run_bench.py        CLI driver that runs workloads, prints metrics to stdout
workloads/          24 benchmark scripts + shared helpers + README.md
tests/              correctness + determinism + driver unit tests
```

Per-workload algorithm references live in
[workloads/README.md](workloads/README.md), grouped by Python sync primitive.
Contributed benchmark runs from different machines live in
[reports/](reports/README.md) — PRs welcome.

## Requirements

- `uv` for environment management.
- `psutil` (declared in `pyproject.toml`); used for peak-RSS on Windows.

## Python versions

The suite runs on any CPython **3.13+**, GIL'd or free-threaded.
Free-threaded is what the benchmark is designed to characterise — on a
GIL'd build most speedups will hover around 1× and that's the expected
result. Each `run_bench.py` invocation prints the actual interpreter
(implementation, version, free-threaded yes/no) at the top of stdout.

The canonical build for the published numbers is **CPython 3.14
free-threaded** (what CI uses). To get it locally:

```sh
uv python install 3.14+freethreaded
uv sync --python 3.14+freethreaded
```

All `uv` command examples in this repository pass `--python
3.14+freethreaded` explicitly so the canonical interpreter is used
regardless of `UV_PYTHON` / `.python-version` / shell state. Substitute
another version (e.g. `--python 3.13`) if you want to compare
interpreter builds.

## Quick start

```sh
uv sync --python 3.14+freethreaded

# List all workloads with their BENCH_SPEC:
uv run --python 3.14+freethreaded python run_bench.py --list

# Run the full suite (24 workloads × 5 runs × serial+parallel):
uv run --python 3.14+freethreaded python run_bench.py

# Parallel only, 3 runs, verbose:
uv run --python 3.14+freethreaded python run_bench.py --mode parallel --runs 3 -v

# Smoke run (small problem sizes, ~10× smaller):
uv run --python 3.14+freethreaded python run_bench.py --smoke
```

## Output

In `--mode both` (the default) the per-workload status line and summary
table compare serial vs parallel:

```
workload  runs  threads  serial wall (s)  parallel wall (s)  ± stdev  speedup  par eff  peak MB  checksum
```

- **serial wall** — mean wall time of `main_serial()`.
- **parallel wall** — mean wall time of `main_parallel()` with the workload's
  `num_threads`.
- **speedup** = `serial_wall_mean / parallel_wall_mean`. > 1.0× means
  parallel beats serial. CPU-bound embarrassingly-parallel workloads
  on free-threaded Python should approach `num_threads`.
- **par eff** = `speedup / num_threads`. 100% means perfect scaling.
- **checksum** — deterministic per-workload value. `*` = unstable across
  runs. `DIVERGENT` = serial and parallel disagree (workload bug).

In `--mode parallel` the table reverts to per-run metrics (wall mean ±
stdev, cpu mean, `cpu eff = cpu_mean / (wall_mean * num_threads)`, peak
MB, checksum). In `--mode serial` it shows just wall / peak / checksum.

## Driver CLI

```
run_bench.py [-h] [--runs N] [--benchmarks LIST]
             [--mode {parallel,serial,both}] [--smoke]
             [--timeout S] [--list] [--verbose]
```

- `--runs N` — runs per (workload, mode) cell (default 5).
- `--benchmarks LIST` — comma-separated subset of workload names.
- `--mode` — `parallel`, `serial`, or `both` (default `both`).
- `--smoke` — sets `BENCH_SMOKE=1` in workloads, scaling problem sizes
  down ~10× for fast iteration.
- `--timeout S` — per-subprocess timeout in seconds (default 600).
- `--list` — print discovered workloads with their `BENCH_SPEC` and exit.
- `--verbose` / `-v` — log every run as it completes.

Exit code is non-zero if any run failed, any checksum was unstable, or
any serial/parallel checksum diverged. **A sub-1.0× speedup is *not*
considered a failure**. The suite is curated for sync-primitive
coverage, not "everything scales".

## Running tests

```sh
uv run --python 3.14+freethreaded pytest tests/ -v
```

Tests set `BENCH_SMOKE=1` so problem sizes shrink ~10×. Every workload
is checked in both modes against the same golden checksum. CI runs the
same command on every push and PR to `main`.

## Adding a workload

1. Add `workloads/<name>.py`. Import `common` for `NUM_THREADS`,
   `parallel_for`, `barrier_workers`, `run_entry`.
2. Implement both `main_parallel()` (multithreaded) and `main_serial()`
   (single-thread baseline). They must return the **same checksum** for
   the same input.
3. Add a module-level `BENCH_SPEC` dict with `name`, `description`,
   `num_threads`, `sync`, `work_units`.
4. End the script with `if __name__ == "__main__": common.run_entry(main_parallel, main_serial)`.
5. Honor `BENCH_SMOKE` — use `common.scaled(full, smoke_value)` for
   problem-size constants.
6. Run the workload once at smoke size and paste the checksum into
   `tests/test_workloads_correct.py` as the golden value.
7. Add a section to [workloads/README.md](workloads/README.md) with
   curated tutorial links for the algorithm.
8. Run `uv run --python 3.14+freethreaded pytest tests/` and
   `uv run --python 3.14+freethreaded pre-commit run --all-files` and
   confirm both pass.
