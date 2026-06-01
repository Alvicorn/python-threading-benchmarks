# Benchmark Report — AMD64 Family 25 Model 68 Stepping 1

- **Date:** 2026-06-01
- **Benchmark commit:** `32a2ecd`
- **Geomean speedup:** 2.28×

## Machine

```
Machine: AMD64 Family 25 Model 68 Stepping 1, AuthenticAMD
Arch:    AMD64 | 8P / 16L cores @ 3.20 GHz | 27.3 GB RAM
OS:      Windows 11 (10.0.26200)
Python:  CPython 3.14.4 (free-threaded: yes)
Commit:  32a2ecd
```

## Command

```sh
uv run --python 3.14+freethreaded python run_bench.py --runs 10 --mode both
```

## Results

| Workload | Sync | Serial (s) | Parallel (s) | Speedup |
|---|---|---:|---:|---:|
| `adaptive_jacobi` | condition | 0.050 | 0.031 | 1.61x |
| `bfs` | none | 0.073 | 0.083 | 0.87x |
| `bitonic_sort` | barrier | 0.649 | 2.603 | 0.25x |
| `bounded_quadsum` | bounded-semaphore | 0.659 | 0.134 | 4.92x |
| `bounded_workers` | bounded-semaphore | 2.027 | 0.594 | 3.42x |
| `concurrent_hashmap` | striped-lock | 0.020 | 0.016 | 1.21x |
| `cv_bounded_buffer` | condition | 0.222 | 0.127 | 1.74x |
| `dining_philosophers` | fork-locks | 0.075 | 0.051 | 1.47x |
| `early_term_search` | event | 0.084 | 0.020 | 4.11x |
| `factorization_pool` | semaphore | 0.054 | 0.028 | 1.92x |
| `fft` | barrier | 0.252 | 0.609 | 0.41x |
| `floyd_warshall` | barrier | 0.197 | 0.053 | 3.74x |
| `matmul` | none | 0.154 | 0.045 | 3.40x |
| `memo_recursion` | rlock | 6.311 | 1.143 | 5.52x |
| `monte_carlo_pi` | none | 0.213 | 0.040 | 5.26x |
| `nested_counter` | rlock | 2.236 | 0.383 | 5.84x |
| `numerical_integration` | none | 0.837 | 0.142 | 5.90x |
| `page_rank` | barrier | 0.228 | 0.186 | 1.23x |
| `password_crack` | none | 0.178 | 0.043 | 4.11x |
| `permit_pool` | semaphore | 5.745 | 1.057 | 5.44x |
| `pollard_factor` | event | 0.021 | 0.018 | 1.21x |
| `prime_sieve` | none | 0.242 | 0.046 | 5.25x |
| `priority_pipeline` | queue | 0.220 | 0.138 | 1.59x |
| `producer_consumer` | queue | 0.220 | 0.119 | 1.85x |

## Raw output

<details>
<summary>Full <code>run_bench.py</code> stdout</summary>

```
Machine: AMD64 Family 25 Model 68 Stepping 1, AuthenticAMD
Arch:    AMD64 | 8P / 16L cores @ 3.20 GHz | 27.3 GB RAM
OS:      Windows 11 (10.0.26200)
Python:  CPython 3.14.4 (free-threaded: yes)
Commit:  32a2ecd

Running 24 workload(s) × 10 run(s) × 2 mode(s) (parallel,serial) = 480 subprocess(es); smoke=False

-> [1/24] adaptive_jacobi      parallel wall= 0.031s  serial wall= 0.050s  speedup= 1.61x  par_eff= 20.2%
-> [2/24] bfs                  parallel wall= 0.083s  serial wall= 0.073s  speedup= 0.87x  par_eff= 10.9%
-> [3/24] bitonic_sort         parallel wall= 2.603s  serial wall= 0.649s  speedup= 0.25x  par_eff=  3.1%
-> [4/24] bounded_quadsum      parallel wall= 0.134s  serial wall= 0.659s  speedup= 4.92x  par_eff= 61.5%
-> [5/24] bounded_workers      parallel wall= 0.594s  serial wall= 2.027s  speedup= 3.42x  par_eff= 42.7%
-> [6/24] concurrent_hashmap   parallel wall= 0.016s  serial wall= 0.020s  speedup= 1.21x  par_eff= 15.2%
-> [7/24] cv_bounded_buffer    parallel wall= 0.127s  serial wall= 0.222s  speedup= 1.74x  par_eff= 21.8%
-> [8/24] dining_philosophers  parallel wall= 0.051s  serial wall= 0.075s  speedup= 1.47x  par_eff= 18.4%
-> [9/24] early_term_search    parallel wall= 0.020s  serial wall= 0.084s  speedup= 4.11x  par_eff= 51.4%
-> [10/24] factorization_pool   parallel wall= 0.028s  serial wall= 0.054s  speedup= 1.92x  par_eff= 24.0%
-> [11/24] fft                  parallel wall= 0.609s  serial wall= 0.252s  speedup= 0.41x  par_eff=  5.2%
-> [12/24] floyd_warshall       parallel wall= 0.053s  serial wall= 0.197s  speedup= 3.74x  par_eff= 46.8%
-> [13/24] matmul               parallel wall= 0.045s  serial wall= 0.154s  speedup= 3.40x  par_eff= 42.5%
-> [14/24] memo_recursion       parallel wall= 1.143s  serial wall= 6.311s  speedup= 5.52x  par_eff= 69.0%
-> [15/24] monte_carlo_pi       parallel wall= 0.040s  serial wall= 0.213s  speedup= 5.26x  par_eff= 65.8%
-> [16/24] nested_counter       parallel wall= 0.383s  serial wall= 2.236s  speedup= 5.84x  par_eff= 73.1%
-> [17/24] numerical_integration parallel wall= 0.142s  serial wall= 0.837s  speedup= 5.90x  par_eff= 73.8%
-> [18/24] page_rank            parallel wall= 0.186s  serial wall= 0.228s  speedup= 1.23x  par_eff= 15.3%
-> [19/24] password_crack       parallel wall= 0.043s  serial wall= 0.178s  speedup= 4.11x  par_eff= 51.4%
-> [20/24] permit_pool          parallel wall= 1.057s  serial wall= 5.745s  speedup= 5.44x  par_eff= 67.9%
-> [21/24] pollard_factor       parallel wall= 0.018s  serial wall= 0.021s  speedup= 1.21x  par_eff= 15.2%
-> [22/24] prime_sieve          parallel wall= 0.046s  serial wall= 0.242s  speedup= 5.25x  par_eff= 65.7%
-> [23/24] priority_pipeline    parallel wall= 0.138s  serial wall= 0.220s  speedup= 1.59x  par_eff= 19.9%
-> [24/24] producer_consumer    parallel wall= 0.119s  serial wall= 0.220s  speedup= 1.85x  par_eff= 23.1%

======================================================================
workload               runs   threads  serial wall (s)  parallel wall (s)  ± stdev  speedup  par eff  peak MB  checksum
---------------------  -----  -------  ---------------  -----------------  -------  -------  -------  -------  --------
adaptive_jacobi        10/10  8        0.050            0.031              0.001    1.61x    20.2%    27.1     7938836
bfs                    10/10  8        0.073            0.083              0.001    0.87x    10.9%    48.0     4973
bitonic_sort           10/10  8        0.649            2.603              0.247    0.25x    3.1%     25.6     4701893
bounded_quadsum        10/10  8        0.659            0.134              0.014    4.92x    61.5%    22.2     8956041
bounded_workers        10/10  8        2.027            0.594              0.079    3.42x    42.7%    24.8     5705378
concurrent_hashmap     10/10  8        0.020            0.016              0.006    1.21x    15.2%    27.8     6297791
cv_bounded_buffer      10/10  8        0.222            0.127              0.005    1.74x    21.8%    24.5     5111357
dining_philosophers    10/10  8        0.075            0.051              0.004    1.47x    18.4%    22.4     960
early_term_search      10/10  8        0.084            0.020              0.001    4.11x    51.4%    24.2     88484
factorization_pool     10/10  8        0.054            0.028              0.007    1.92x    24.0%    22.7     1998560
fft                    10/10  8        0.252            0.609              0.036    0.41x    5.2%     36.6     1142602
floyd_warshall         10/10  8        0.197            0.053              0.003    3.74x    46.8%    23.1     8421045
matmul                 10/10  8        0.154            0.045              0.004    3.40x    42.5%    24.2     6535330
memo_recursion         10/10  8        6.311            1.143              0.112    5.52x    69.0%    22.6     4881333
monte_carlo_pi         10/10  8        0.213            0.040              0.007    5.26x    65.8%    22.4     1257606
nested_counter         10/10  8        2.236            0.383              0.045    5.84x    73.1%    22.6     4000408
numerical_integration  10/10  8        0.837            0.142              0.018    5.90x    73.8%    22.3     3987766
page_rank              10/10  8        0.228            0.186              0.004    1.23x    15.3%    28.4     9998118
password_crack         10/10  8        0.178            0.043              0.005    4.11x    51.4%    23.9     754
permit_pool            10/10  8        5.745            1.057              0.149    5.44x    67.9%    42.4     327526
pollard_factor         10/10  8        0.021            0.018              0.000    1.21x    15.2%    22.5     9346167
prime_sieve            10/10  8        0.242            0.046              0.011    5.25x    65.7%    25.9     148933
priority_pipeline      10/10  8        0.220            0.138              0.009    1.59x    19.9%    24.6     5111357
producer_consumer      10/10  8        0.220            0.119              0.005    1.85x    23.1%    24.2     5111357
======================================================================

speedup = serial_wall_mean / parallel_wall_mean

par eff = speedup / num_threads
'*' on checksum = unstable across runs;  'DIVERGENT' = serial and parallel disagree.
```

</details>
