# Benchmark Report — Intel64 Family 6 Model 170 Stepping 4

- **Date:** 2026-06-01
- **Benchmark commit:** `32a2ecd`
- **Geomean speedup:** 1.69×

## Machine

```
Machine: Intel64 Family 6 Model 170 Stepping 4, GenuineIntel
Arch:    AMD64 | 16P / 22L cores @ 1.40 GHz | 31.5 GB RAM
OS:      Windows 11 (10.0.26200)
Python:  CPython 3.14.5 (free-threaded: yes)
Commit:  32a2ecd
```

## Command

```sh
uv run --python 3.14+freethreaded python run_bench.py --runs 10 --mode both
```

## Results

| Workload | Sync | Serial (s) | Parallel (s) | Speedup |
|---|---|---:|---:|---:|
| `adaptive_jacobi` | condition | 0.064 | 0.045 | 1.43x |
| `bfs` | none | 0.106 | 0.117 | 0.90x |
| `bitonic_sort` | barrier | 1.013 | 9.242 | 0.11x |
| `bounded_quadsum` | bounded-semaphore | 0.755 | 0.202 | 3.73x |
| `bounded_workers` | bounded-semaphore | 1.967 | 0.638 | 3.08x |
| `concurrent_hashmap` | striped-lock | 0.022 | 0.019 | 1.12x |
| `cv_bounded_buffer` | condition | 0.230 | 0.167 | 1.38x |
| `dining_philosophers` | fork-locks | 0.084 | 0.041 | 2.07x |
| `early_term_search` | event | 0.083 | 0.041 | 2.03x |
| `factorization_pool` | semaphore | 0.056 | 0.023 | 2.47x |
| `fft` | barrier | 0.277 | 1.455 | 0.19x |
| `floyd_warshall` | barrier | 0.197 | 0.106 | 1.85x |
| `matmul` | none | 0.171 | 0.088 | 1.95x |
| `memo_recursion` | rlock | 6.256 | 1.552 | 4.03x |
| `monte_carlo_pi` | none | 0.193 | 0.049 | 3.98x |
| `nested_counter` | rlock | 2.140 | 0.418 | 5.12x |
| `numerical_integration` | none | 0.817 | 0.184 | 4.43x |
| `page_rank` | barrier | 0.219 | 0.373 | 0.59x |
| `password_crack` | none | 0.176 | 0.081 | 2.18x |
| `permit_pool` | semaphore | 6.052 | 1.197 | 5.05x |
| `pollard_factor` | event | 0.025 | 0.022 | 1.13x |
| `prime_sieve` | none | 0.244 | 0.074 | 3.31x |
| `priority_pipeline` | queue | 0.215 | 0.154 | 1.39x |
| `producer_consumer` | queue | 0.217 | 0.154 | 1.41x |

## Raw output

<details>
<summary>Full <code>run_bench.py</code> stdout</summary>

```
Machine: Intel64 Family 6 Model 170 Stepping 4, GenuineIntel
Arch:    AMD64 | 16P / 22L cores @ 1.40 GHz | 31.5 GB RAM
OS:      Windows 11 (10.0.26200)
Python:  CPython 3.14.5 (free-threaded: yes)
Commit:  32a2ecd

Running 24 workload(s) × 10 run(s) × 2 mode(s) (parallel,serial) = 480 subprocess(es); smoke=False

-> [1/24] adaptive_jacobi      parallel wall= 0.045s  serial wall= 0.064s  speedup= 1.43x  par_eff= 17.8%
-> [2/24] bfs                  parallel wall= 0.117s  serial wall= 0.106s  speedup= 0.90x  par_eff= 11.3%
-> [3/24] bitonic_sort         parallel wall= 9.242s  serial wall= 1.013s  speedup= 0.11x  par_eff=  1.4%
-> [4/24] bounded_quadsum      parallel wall= 0.202s  serial wall= 0.755s  speedup= 3.73x  par_eff= 46.7%
-> [5/24] bounded_workers      parallel wall= 0.638s  serial wall= 1.967s  speedup= 3.08x  par_eff= 38.5%
-> [6/24] concurrent_hashmap   parallel wall= 0.019s  serial wall= 0.022s  speedup= 1.12x  par_eff= 14.0%
-> [7/24] cv_bounded_buffer    parallel wall= 0.167s  serial wall= 0.230s  speedup= 1.38x  par_eff= 17.3%
-> [8/24] dining_philosophers  parallel wall= 0.041s  serial wall= 0.084s  speedup= 2.07x  par_eff= 25.9%
-> [9/24] early_term_search    parallel wall= 0.041s  serial wall= 0.083s  speedup= 2.03x  par_eff= 25.3%
-> [10/24] factorization_pool   parallel wall= 0.023s  serial wall= 0.056s  speedup= 2.47x  par_eff= 30.8%
-> [11/24] fft                  parallel wall= 1.455s  serial wall= 0.277s  speedup= 0.19x  par_eff=  2.4%
-> [12/24] floyd_warshall       parallel wall= 0.106s  serial wall= 0.197s  speedup= 1.85x  par_eff= 23.1%
-> [13/24] matmul               parallel wall= 0.088s  serial wall= 0.171s  speedup= 1.95x  par_eff= 24.3%
-> [14/24] memo_recursion       parallel wall= 1.552s  serial wall= 6.256s  speedup= 4.03x  par_eff= 50.4%
-> [15/24] monte_carlo_pi       parallel wall= 0.049s  serial wall= 0.193s  speedup= 3.98x  par_eff= 49.7%
-> [16/24] nested_counter       parallel wall= 0.418s  serial wall= 2.140s  speedup= 5.12x  par_eff= 64.0%
-> [17/24] numerical_integration parallel wall= 0.184s  serial wall= 0.817s  speedup= 4.43x  par_eff= 55.4%
-> [18/24] page_rank            parallel wall= 0.373s  serial wall= 0.219s  speedup= 0.59x  par_eff=  7.3%
-> [19/24] password_crack       parallel wall= 0.081s  serial wall= 0.176s  speedup= 2.18x  par_eff= 27.3%
-> [20/24] permit_pool          parallel wall= 1.197s  serial wall= 6.052s  speedup= 5.05x  par_eff= 63.2%
-> [21/24] pollard_factor       parallel wall= 0.022s  serial wall= 0.025s  speedup= 1.13x  par_eff= 14.2%
-> [22/24] prime_sieve          parallel wall= 0.074s  serial wall= 0.244s  speedup= 3.31x  par_eff= 41.4%
-> [23/24] priority_pipeline    parallel wall= 0.154s  serial wall= 0.215s  speedup= 1.39x  par_eff= 17.4%
-> [24/24] producer_consumer    parallel wall= 0.154s  serial wall= 0.217s  speedup= 1.41x  par_eff= 17.6%

======================================================================
workload               runs   threads  serial wall (s)  parallel wall (s)  ± stdev  speedup  par eff  peak MB  checksum
---------------------  -----  -------  ---------------  -----------------  -------  -------  -------  -------  --------
adaptive_jacobi        10/10  8        0.064            0.045              0.005    1.43x    17.8%    27.2     7938836
bfs                    10/10  8        0.106            0.117              0.009    0.90x    11.3%    47.0     4973
bitonic_sort           10/10  8        1.013            9.242              0.728    0.11x    1.4%     25.7     4701893
bounded_quadsum        10/10  8        0.755            0.202              0.032    3.73x    46.7%    22.2     8956041
bounded_workers        10/10  8        1.967            0.638              0.051    3.08x    38.5%    23.9     5705378
concurrent_hashmap     10/10  8        0.022            0.019              0.003    1.12x    14.0%    27.9     6297791
cv_bounded_buffer      10/10  8        0.230            0.167              0.015    1.38x    17.3%    24.4     5111357
dining_philosophers    10/10  8        0.084            0.041              0.002    2.07x    25.9%    22.5     960
early_term_search      10/10  8        0.083            0.041              0.005    2.03x    25.3%    24.0     88484
factorization_pool     10/10  8        0.056            0.023              0.005    2.47x    30.8%    22.7     1998560
fft                    10/10  8        0.277            1.455              0.207    0.19x    2.4%     36.6     1142602
floyd_warshall         10/10  8        0.197            0.106              0.009    1.85x    23.1%    23.2     8421045
matmul                 10/10  8        0.171            0.088              0.007    1.95x    24.3%    24.0     6535330
memo_recursion         10/10  8        6.256            1.552              0.163    4.03x    50.4%    22.5     4881333
monte_carlo_pi         10/10  8        0.193            0.049              0.005    3.98x    49.7%    22.3     1257606
nested_counter         10/10  8        2.140            0.418              0.035    5.12x    64.0%    22.4     4000408
numerical_integration  10/10  8        0.817            0.184              0.007    4.43x    55.4%    22.2     3987766
page_rank              10/10  8        0.219            0.373              0.021    0.59x    7.3%     28.4     9998118
password_crack         10/10  8        0.176            0.081              0.004    2.18x    27.3%    23.8     754
permit_pool            10/10  8        6.052            1.197              0.113    5.05x    63.2%    41.1     327526
pollard_factor         10/10  8        0.025            0.022              0.005    1.13x    14.2%    22.5     9346167
prime_sieve            10/10  8        0.244            0.074              0.013    3.31x    41.4%    23.8     148933
priority_pipeline      10/10  8        0.215            0.154              0.007    1.39x    17.4%    24.6     5111357
producer_consumer      10/10  8        0.217            0.154              0.014    1.41x    17.6%    24.3     5111357
======================================================================

speedup = serial_wall_mean / parallel_wall_mean

par eff = speedup / num_threads
'*' on checksum = unstable across runs;  'DIVERGENT' = serial and parallel disagree.
```

</details>
