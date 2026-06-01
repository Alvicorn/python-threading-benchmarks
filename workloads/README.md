# Workload References

Curated tutorial references for each workload's underlying algorithm,
grouped by the `threading` synchronization primitive it features.

Every workload also has a `BENCH_SPEC` dict at the top of its module
documenting `num_threads`, `sync`, and `work_units`; run
`uv run --python 3.14+freethreaded python run_bench.py --list` to see
them all at once.

---

## No synchronization (embarrassingly parallel)

These workloads partition work across threads with no shared writes;
the only sync is the implicit join at the end. They're useful as
"upper bound" reference points for what scaling looks like when nothing
contends.

### `monte_carlo_pi` — Estimate π by dart-throwing in the unit square
- [Wikipedia: Pi — Monte Carlo methods](https://en.wikipedia.org/wiki/Pi#Monte_Carlo_methods).

### `password_crack` — Brute-force SHA-256 hash search
- [Wikipedia: SHA-2](https://en.wikipedia.org/wiki/SHA-2).

### `matmul` — Pure-Python triple-loop matrix multiply, row-parallel
- [Wikipedia: Matrix multiplication algorithm](https://en.wikipedia.org/wiki/Matrix_multiplication_algorithm).

### `numerical_integration` — Composite Simpson's rule
- [Wikipedia: Simpson's rule](https://en.wikipedia.org/wiki/Simpson%27s_rule) — derivation + composite formula.

### `prime_sieve` — Segmented Sieve of Eratosthenes
- [Wikipedia: Sieve of Eratosthenes](https://en.wikipedia.org/wiki/Sieve_of_Eratosthenes).

### `bfs` — Level-parallel breadth-first search
- [Wikipedia: Breadth-first search](https://en.wikipedia.org/wiki/Breadth-first_search) — pseudocode + worked example. Per-thread frontiers are merged by the main thread after `parallel_for` joins, so no shared lock is needed during expansion.

---

## Lock

### `concurrent_hashmap` — Striped concurrent hash map
- [Wikipedia: Concurrent hash table](https://en.wikipedia.org/wiki/Concurrent_hash_table) — covers stripe locking as the canonical approach.
- [Wikipedia: Lock granularity](https://en.wikipedia.org/wiki/Lock_(computer_science)#Granularity).

### `dining_philosophers` — Resource-hierarchy fork-locking
- [Wikipedia: Dining philosophers problem](https://en.wikipedia.org/wiki/Dining_philosophers_problem) — Dijkstra's original problem statement and several solution variants.

---

## RLock (re-entrant lock)

### `memo_recursion` — Per-thread RLock-guarded memoization cache
- [Wikipedia: Reentrant mutex](https://en.wikipedia.org/wiki/Reentrant_mutex) — what an RLock is and when you need re-entrancy.
- [Wikipedia: Memoization](https://en.wikipedia.org/wiki/Memoization).

### `nested_counter` — Monitor pattern with nested public/private methods
- [Wikipedia: Monitor (synchronization)](https://en.wikipedia.org/wiki/Monitor_(synchronization)) — the "every method takes the lock; methods call each other" idiom that justifies RLock.

---

## Event

### `early_term_search` — Brute-force SHA-256 search with Event-driven early termination
- [Wikipedia: SHA-2](https://en.wikipedia.org/wiki/SHA-2).


### `pollard_factor` — Pollard's rho factorisation, first-to-find wins
- [Wikipedia: Pollard's rho algorithm](https://en.wikipedia.org/wiki/Pollard%27s_rho_algorithm) — has pseudocode for the rho cycle-detection step.

---

## Condition

### `adaptive_jacobi` — Condition-coordinated Jacobi solver with adaptive iteration count
- [Wikipedia: Jacobi method](https://en.wikipedia.org/wiki/Jacobi_method) — the linear-solver algorithm.

### `cv_bounded_buffer` — Hand-rolled bounded buffer using Condition + deque
- [Wikipedia: Producer–consumer problem](https://en.wikipedia.org/wiki/Producer%E2%80%93consumer_problem) — the classic problem this buffer solves.

---

## Semaphore

### `permit_pool` — Worker pool with Semaphore-managed permits, SHA-256 hashing per task
- [Python `threading.Semaphore` docs](https://docs.python.org/3/library/threading.html#semaphore-objects).

### `factorization_pool` — Worker pool with Semaphore permits, trial-division factorisation per task
- [Wikipedia: Trial division](https://en.wikipedia.org/wiki/Trial_division) — the per-task algorithm.

---

## BoundedSemaphore

### `bounded_workers` — Worker pool with BoundedSemaphore permits, polynomial evaluation per task
- [Wikipedia: Horner's method](https://en.wikipedia.org/wiki/Horner%27s_method) — the polynomial evaluation scheme each task uses.

### `bounded_quadsum` — Worker pool with BoundedSemaphore permits, sum-of-squares per task
- [Python `threading.BoundedSemaphore` docs](https://docs.python.org/3/library/threading.html#threading.BoundedSemaphore).

---

## Barrier

### `bitonic_sort` — Stage-parallel bitonic sort
- [Wikipedia: Bitonic sorter](https://en.wikipedia.org/wiki/Bitonic_sorter) — diagrams + the (k, j) compare-swap structure we implement.

### `fft` — Iterative Cooley-Tukey radix-2 FFT, barrier per stage
- [Wikipedia: Cooley–Tukey FFT algorithm](https://en.wikipedia.org/wiki/Cooley%E2%80%93Tukey_FFT_algorithm) — derivation + pseudocode.
- Jake VanderPlas: ["Understanding the FFT Algorithm"](https://jakevdp.github.io/blog/2013/08/28/understanding-the-fft/) — implements the FFT in NumPy from scratch and explains the bit-reverse + butterfly structure.

### `floyd_warshall` — All-pairs shortest paths, barrier per outer iteration
- [Wikipedia: Floyd–Warshall algorithm](https://en.wikipedia.org/wiki/Floyd%E2%80%93Warshall_algorithm) — has pseudocode and a worked example.

### `page_rank` — PageRank power iteration on a sparse graph, barrier per iteration
- [Wikipedia: PageRank](https://en.wikipedia.org/wiki/PageRank) — the damped-random-surfer derivation.

---

## queue (`queue.Queue` / `queue.PriorityQueue` — built on Condition + Lock)

### `producer_consumer` — Bounded `queue.Queue` with producer and consumer threads
- [Wikipedia: Producer–consumer problem](https://en.wikipedia.org/wiki/Producer%E2%80%93consumer_problem).
- [Python `queue.Queue` docs](https://docs.python.org/3/library/queue.html#queue.Queue) — built on Condition + Lock internally.

### `priority_pipeline` — Same shape with `queue.PriorityQueue`
- [Python `queue.PriorityQueue` docs](https://docs.python.org/3/library/queue.html#queue.PriorityQueue) — heap-ordered variant of `queue.Queue`.
