# Experiments and limits of the evidence

[简体中文](../zh/EXPERIMENTS.md) · [Home](../../README.md) · [Research contract](RESEARCH.md)

## Main finding

On this Apple M1 Pro CPU run, spherical-cap pruning achieved **10.20× median single-query speedup** over a contiguous float64 scan on the prespecified **synthetic clustered 50,000×64, k=10** workload, scoring **2.34%** of vectors on average. The benefit is strongly distribution-dependent: **real digits took 4.40× as long as scan**, isotropic 50,000×64 took **1.60×**, and the 32-vector, k=N boundary case took **3.69×**. These negative results are part of the delivered evidence. This is neither a pretrained-embedding benchmark nor an application end-to-end result.

## Record, source, and environment

The full record is [results/reference.json](../../results/reference.json), run ID `140ea5bb-9c95-4e8a-b2ab-17bcde0903ca`. It ran from `2026-09-21T12:20:21.157225+00:00` to `2026-09-21T12:20:31.138783+00:00` with `python benchmark.py --output results/reference.json`. Its source snapshot names Git revision `0f8260de8bd9de459de4d5f63cd86fb81cf08aca` and aggregate SHA-256 `cd50eb987f9d56f1a1e778a5b41127097aeb0115ccb52787ec05c862aec8c530`; per-file hashes identify the tested implementation, benchmark, configuration, lockfile, and checks. Subsequent documentation or validation-record commits do not retroactively change this run's provenance.

The inspected host has an Apple M1 Pro, 16 GiB unified memory, arm64 macOS (Darwin 25.6.0), Python 3.12.2, NumPy 2.2.6 using Apple Accelerate, scikit-learn 1.7.2, threadpoolctl 3.6.0, and psutil 7.1.0. The runner requests one thread by setting `VECLIB_MAXIMUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, and `OMP_NUM_THREADS=1` before NumPy import and entering `threadpool_limits(1)`. **Accelerate's actual runtime thread count is not introspectable through threadpoolctl**; the recorded OpenMP count of 1 is not independent proof of Accelerate's internal thread count. All modes share the same request and process. This is a requested single-thread experiment, not a measured CPU-affinity guarantee.

No GPU or asynchronous device path is used, so no device synchronization is needed. Docker was unavailable and container validation was not executed. No result is claimed for Linux, CUDA, Metal, other CPUs, remote CI, or a production deployment.

## Frozen target, expectation, and measurement

[configs/protocol.json](../../configs/protocol.json) was written before the official measurement. Its targets were not adjusted to the result.

| Class | Statement | Outcome |
|---|---|---|
| Target | At least 1.50× median speedup for `clustered_n50000_d64`. | Measured 10.20×; met in this run. |
| Target | At most 30% mean evaluated-vector fraction on that case. | Measured 2.34%; met in this run. |
| Correctness acceptance | Identical ordered IDs; scores within `atol=1e-12, rtol=1e-12` against scan. | Passed for all 5,880 recorded calls; largest absolute score difference 4.44e-16. |
| Expected, conditional | Tight separated caps can reject most blocks; loose caps or small workloads can lose to scan. | Favorable synthetic and unfavorable cases support this workload-dependent explanation. |
| Theoretical, conditional | Full build can amortize after enough faster queries. | An estimated 215 primary-case queries, using measured medians; not a measured deployment break-even. |

## Workloads and fair comparison

The protocol covers seven cases, each with 40 query vectors, seven repetitions, and three modes: **7 × 40 × 7 × 3 = 5,880 timed calls**. There are **280 timings per mode per case, but only 40 distinct queries**, reused across repetitions. These are not 280 independent datasets or a multi-host study. Seeds are `20260921 + case_index`; input-array hashes are saved in each raw case.

- Synthetic clustered cases use random unit centers plus Gaussian noise with standard deviation 0.035: 5,000×64 (32 generating/requested clusters), 50,000×64 (64), 50,000×128 (64), and 50,000×64 with k=100 (64). The other clustered cases use k=10. Six spherical k-means rounds build each index. Empty clusters can be removed; actual block counts are recorded.
- Synthetic isotropic cases use independent Gaussian vectors and queries: 50,000×64, k=10, 64 clusters; and the 32×8 boundary case with k=32 and eight clusters.
- `digits_real` uses scikit-learn 1.7.2's bundled `load_digits` raw 8×8 pixel intensities. A seeded permutation supplies 40 held-out query rows and 1,757 index rows, with k=10 and 32 clusters. It uses no trained model or embedding network and measures numerical retrieval, not classification accuracy or semantic relevance. Dataset attribution is retained in [NOTICE](../../NOTICE.md).

All modes use the same normalized float64 vectors, queries, k, thread request, and deterministic score/ID top-k routine. `scan` is a practical contiguous NumPy/BLAS matrix-vector product plus partial selection; it is not a Python row-by-row strawman. `blocked` uses the packed layout and visits every block without computing bounds, isolating the effect of bound-driven pruning from packing, dispatch, and merging overhead. `pruned` calculates bounds, orders blocks, and skips only provably uncompetitive blocks subject to the documented float64 guard.

The retained original layout exists to support the scan baseline, while the packed layout supports block traversal. Both reside in the same index during measurement, making this a latency comparison with a shared memory budget, not a claim that the pruning index uses less memory than a scan-only implementation. The matrix-query API processes one query at a time. It is not a large-batch GEMM baseline or a comparison with Faiss, approximate indexes, or float32 retrieval.

## Timing and statistics

`perf_counter_ns()` surrounds each `index.search(query, k, mode=...)`. Timed work includes input validation and query normalization, bound computation when enabled, vector scoring, selection/merging, and result allocation. Data generation, index construction, save/load, the scan correctness oracle, and verification of returned results are outside these search timers. Construction and serialization costs are reported separately below. No JIT compilation is used.

Each mode gets four warmup queries. Within each repetition, query order is permuted and mode order is independently permuted for each query, reducing fixed-order bias. All valid samples are retained. Median and the 25th–75th percentile interval below describe the empirical timing distribution; they are not confidence intervals. Seven per-repeat medians remain available in [summary.json](../../results/analysis/summary.json). No p95/p99, statistical-significance, concurrent-throughput, or service-level claim is made.

`first_query_ns` is the first timed call **after** index creation, serialization, roundtrip queries, and the scan reference calculation. It is **not cold process startup or cold-cache latency**. On the primary case these calls were 1.1943 ms scan, 1.6838 ms blocked, and 0.1161 ms pruned. The experiment does not measure interpreter startup, initial imports, dependency installation, or an application workflow.

## Complete measured latency table

The following values are calculated directly from the saved samples. The reusable generation script emits [English](../../results/analysis/table_en.md) and [Chinese](../../results/analysis/table_zh.md) tables and [machine-readable statistics](../../results/analysis/summary.json).

| Case | Scan ms, median [Q1, Q3] | Blocked ms, median [Q1, Q3] | Pruned ms, median [Q1, Q3] | Scan/Pruned | Scored | Samples/mode |
|---|---:|---:|---:|---:|---:|---:|
| clustered_n5000_d64 | 0.1015 [0.0928, 0.1124] | 0.3225 [0.3161, 0.3412] | 0.0464 [0.0408, 0.0505] | 2.19× | 4.92% | 280 |
| clustered_n50000_d64 | 0.9159 [0.7899, 1.0245] | 1.6033 [1.5798, 1.6379] | 0.0898 [0.0848, 0.0993] | 10.20× | 2.34% | 280 |
| clustered_n50000_d128 | 1.4321 [1.3256, 1.5199] | 2.0885 [2.0661, 2.1112] | 0.1140 [0.1015, 0.1470] | 12.56× | 3.07% | 280 |
| isotropic_n50000_d64 | 1.0157 [0.9303, 1.1119] | 1.6096 [1.5708, 1.6439] | 1.6252 [1.5942, 1.6572] | 0.62× | 100.00% | 280 |
| clustered_n50000_k100 | 0.9809 [0.8693, 1.0899] | 1.8960 [1.8733, 1.9293] | 0.0981 [0.0890, 0.1074] | 10.00× | 2.77% | 280 |
| digits_real | 0.0512 [0.0462, 0.0540] | 0.2590 [0.2559, 0.2620] | 0.2251 [0.1925, 0.2589] | 0.23× | 84.36% | 280 |
| tiny_k_equals_n | 0.0170 [0.0169, 0.0174] | 0.0512 [0.0508, 0.0517] | 0.0629 [0.0625, 0.0640] | 0.27× | 100.00% | 280 |

![Measured speedup and evaluated-vector fraction](../../results/analysis/benchmark.png)

`Scan/Pruned < 1` means pruning is slower. The figure summarizes the same data, including all unfavorable cases; it does not select the best repetition.

## Throughput and amortization

QPS below is `sample_count / sum(timed_search_seconds)`. It is sequential timed-call throughput, excluding the harness's correctness checks and setup; it is not server throughput. The conditional break-even estimate is `ceil(full_build_ms / (scan_median_ms - pruned_median_ms))`. Charging the entire build is conservative with respect to preprocessing that a scan would also need, but it still excludes save/load and is a calculation from medians, not an observed application result. A nonpositive per-query saving has no benefit to amortize.

| Case | Scan QPS | Blocked QPS | Pruned QPS | Full-build break-even estimate |
|---|---:|---:|---:|---:|
| clustered_n5000_d64 | 9341 | 2946 | 19895 | 295 |
| clustered_n50000_d64 | 1113 | 620 | 10804 | 215 |
| clustered_n50000_d128 | 704 | 476 | 8142 | 237 |
| isotropic_n50000_d64 | 988 | 621 | 615 | No benefit |
| clustered_n50000_k100 | 1023 | 527 | 9768 | 194 |
| digits_real | 19931 | 3838 | 4454 | No benefit |
| tiny_k_equals_n | 57070 | 19050 | 15544 | No benefit |

## Construction, persistence, and memory

Build, save, and load each have **one measurement per case**, so their displayed precision must not be interpreted as a latency distribution. Build includes normalization, clustering, packing, and cap construction. Save includes compressed NPZ serialization and filesystem write; load includes reading, validation, and certificate reconstruction. A primary-case index therefore also required a measured 177.159 ms build, 764.400 ms save, and 88.470 ms load. These costs matter for reuse and startup and are not concealed in the query speedup.

| Case | Build ms | Save ms | Load ms | Index arrays MiB | File MiB | RSS after build MiB | Cumulative peak RSS MiB |
|---|---:|---:|---:|---:|---:|---:|---:|
| clustered_n5000_d64 | 16.214 | 77.094 | 9.177 | 4.974 | 2.343 | 123.859 | 133.812 |
| clustered_n50000_d64 | 177.159 | 764.400 | 88.470 | 49.623 | 23.427 | 218.406 | 311.062 |
| clustered_n50000_d128 | 311.521 | 1457.715 | 161.685 | 98.480 | 46.801 | 514.000 | 568.000 |
| isotropic_n50000_d64 | 168.639 | 719.855 | 90.792 | 49.623 | 23.428 | 568.578 | 570.328 |
| clustered_n50000_k100 | 170.587 | 730.253 | 88.479 | 49.623 | 23.426 | 568.969 | 571.938 |
| digits_real | 6.565 | 12.962 | 2.787 | 1.759 | 0.192 | 571.828 | 573.391 |
| tiny_k_equals_n | 0.646 | 0.961 | 0.798 | 0.005 | 0.003 | 573.891 | 577.266 |

One MiB is 2²⁰ bytes. `index_array_bytes` is the sum of retained index ndarray payloads, including original and packed vectors; it excludes Python objects and temporary/BLAS allocations. `process_rss_after_build_bytes` is a point-in-time process RSS including interpreter, inputs, and retained allocator memory. `process_peak_rss_after_bytes` is the **cumulative process high-water mark**, including prior cases, construction, and I/O. The tiny case's 577.266 MiB peak is not the tiny index's memory requirement: its retained index arrays occupy only 5,256 bytes. These measurements cannot identify per-search-mode peak memory or demonstrate memory savings over scan.

The 16 MiB assignment-matrix budget limits only clustering score scratch space. It is not a total memory limit. The largest measured index arrays were 98.480 MiB for 50,000×128. No out-of-memory result, timeout, or numerical failure occurred in this official run; raw statuses remain `passed` for all seven cases. Performance losses remain in the dataset even though correctness passed.

## Interpretation, ablation, and limitations

On the primary favorable distribution, blocked traversal took 1.6033 ms versus scan's 0.9159 ms, while pruning reduced latency to 0.0898 ms and scored 2.34% of vectors. Thus packing and block traversal alone do not explain the gain; avoiding most scores and merges is necessary. The block ablation also changes traversal from bound order to storage order, so it does not isolate every possible order/selection interaction.

Isotropic data scored 100% of vectors and lost about 1.60× to scan: broad caps supplied no useful rejection, leaving dispatch, bounds, and merging overhead. The real digits case still scored 84.36% of vectors and took 4.40× as long as scan; modest work reduction could not repay overhead on a small collection. With k=N, all candidates are required and the tiny case took 3.69× as long. These results reject any claim of universal exact-search acceleration and favor scan for these measured inputs.

The k=10 and k=100 clustered cases use different seeds and therefore different datasets. They demonstrate two supported workloads, **not a controlled isolated k ablation**. Likewise, cross-size comparisons are coverage, not a scaling law with every other factor fixed. One host, one seeded dataset per case, 40 queries, requested threads, float64 arithmetic, and tight synthetic clusters limit generalization. The numerical tests establish the declared agreement on these inputs, not a formal proof for every IEEE-754/BLAS edge case. New embedding datasets, seed sweeps, cluster-count sweeps, an adaptive scan fallback, and tighter/hierarchical bounds are future research directions, not delivered features.

## Reproduce and retain evidence

From the project root after the locked development installation:

```sh
.venv/bin/python benchmark.py --output results/reproduction.json
.venv/bin/python scripts/validate_results.py results/reproduction.json
.venv/bin/python scripts/analyze.py results/reproduction.json --output-dir results/reproduction-analysis
.venv/bin/python -m pytest -q
```

Choose a fresh output name each time; the benchmark refuses to overwrite an existing result. `--smoke` is an explicitly smaller check and must not replace the official workload. Preserve valid samples and failures, their source snapshots, and protocol differences. Keep hardware/software and thread disclosures with any copied table. [DEVELOPMENT.md](DEVELOPMENT.md) and [the acceptance record](../../results/acceptance/checks.json) track engineering validation separately from benchmark performance.
