# Project description and evidence

[简体中文](../zh/RESUME.md) · [Home](../../README.md) · [Measured results](EXPERIMENTS.md)

**CapPrune — an auditable CPU exact-cosine index using spherical-cap bounds.** These are evidence-based project-description drafts; they describe repository outcomes rather than certify personal mastery, authorship history, or production experience. The corresponding Chinese bullets use the same scope and numbers.

## Resume bullets

1. Implemented a float64 CPU cosine top-k engine with spherical k-means blocks, contiguous vector packing, conservative spherical-cap bounds, and deterministic row-ID ties; validated exact ordered IDs against a practical BLAS scan across seven workloads, including a 50,000-vector, 128-dimensional case. The geometric bound and clustering method are established prior work.
2. Reduced median single-query latency from **0.9159 ms to 0.0898 ms (10.20×)** on **synthetic clustered 50,000×64 vectors, k=10**, using an Apple M1 Pro with a requested one-thread Accelerate budget; scored **2.34%** of vectors on average. These measurements exclude build/load and use float64 scan plus partial top-k as the baseline; Accelerate's actual thread count was not introspectable.
3. Designed a pruning-disabled block ablation and retained unfavorable cases: raw-pixel digits, isotropic vectors, and k=N were respectively **4.40×, 1.60×, and 3.69× slower** than scan. Used scoring counters and setup costs to identify distribution and reuse requirements; the primary index took **177.159 ms** to build, with a conditional full-build break-even estimate of **215 queries**.
4. Delivered an immutable, reusable Python API, bilingual CLI, validated NPZ persistence with reconstructed certificates, locked dependencies, and reproducible benchmark evidence with source hashes. **5,880 timed calls** preserved ordered IDs and the declared score tolerance (maximum absolute error **4.44e-16**); **70 local automated tests passed**, and a clean isolated wheel installation and offline demo were verified. The same 70 tests, package build, benchmark smoke and Docker build/run also passed in [Ubuntu 24.04 GitHub Actions](https://github.com/hardwork-xu/cosine-vector-search/actions/runs/35602650743).

## Evidence index

| Claim | Implementation and protocol | Evidence |
|---|---|---|
| Bullet 1: core mechanism and exact results | [Core implementation](../../src/capprune/index.py), [research and originality boundary](RESEARCH.md), [core tests](../../tests/test_core.py) | [Raw results](../../results/reference.json): seven `cases`, ordered-ID and score checks; `clustered_n50000_d128`. |
| Bullet 2: constrained speedup | [Frozen protocol](../../configs/protocol.json), [benchmark runner](../../benchmark.py) | [Summary](../../results/analysis/summary.json): `clustered_n50000_d64`; [full distributions and environment limits](EXPERIMENTS.md). |
| Bullet 3: ablation, failures, setup | `search(mode="blocked")` in [index.py](../../src/capprune/index.py); identical precision and result contract | [Raw results](../../results/reference.json): `build_ns`, all three modes, digits/isotropic/tiny cases; [amortization calculation](../../scripts/analyze.py). |
| Bullet 4: reliable interface and reproducibility | [CLI](../../src/capprune/cli.py), [CLI tests](../../tests/test_cli.py), [benchmark tests](../../tests/test_benchmark.py), [lockfile](../../uv.lock) | [Acceptance commands and statuses](../../results/acceptance/checks.json), [unit test log](../../results/acceptance/unit_tests.log), [clean install](../../results/acceptance/clean_install.log), [clean demo](../../results/acceptance/clean_demo.log), [raw source hashes](../../results/reference.json). |

The 70-test result covers the full local suite; integration checks may rerun part of that suite and must not be added as unique tests. The 5,880 timings contain repeated queries: 40 distinct queries per case, seven repetitions, and three modes. Do not shorten the performance bullet by removing “synthetic,” precision, baseline, hardware, or build/load exclusions. There is no evidence of deployment, users, business impact, publication acceptance, general superiority over retrieval libraries, or model-inference acceleration.

## Brief project presentation

**Why this problem.** I want to study a concrete tension in retrieval: fewer dot products do not necessarily mean faster search. An exact CPU index makes the pruning decision, overhead, and result agreement visible without relying on model downloads or approximate-recall tradeoffs.

**How it works.** Normalize vectors, form spherical k-means blocks, store each block contiguously, and compute a conservative spherical cap containing its members. Search orders blocks by a query-specific upper bound and stops only when the remaining bound is strictly below the kth actual score. Score ties retain the smaller original row ID.

**Key tradeoff.** The flat index is inspectable, but stores both original and packed vectors and pays Python traversal/top-k merging overhead. The baseline uses a contiguous BLAS scan. Build and persistence costs matter when an index is not reused enough.

**Most informative experiment.** On the favorable 50,000×64 synthetic workload, scan, blocked, and pruned medians were 0.9159, 1.6033, and 0.0898 ms. Block traversal alone was slower; pruning's reduction to 2.34% scored vectors explains the favorable result more directly than a headline speedup alone.

**Failure and limits.** Real digits were 4.40× slower than scan despite some pruning. High-dimensional isotropic caps rejected nothing, and k=N required every vector. Results cover one CPU host, float64, and online batch size one; they do not establish large-batch throughput, real-embedding benefits, GPU support, or formal floating-point correctness for every backend.

**Next research question.** Can an index choose scan versus pruning from inexpensive geometry/workload diagnostics, and do hierarchical or tighter bounds repay their added cost on actual embedding datasets? Those questions require new implementations and controlled multi-seed experiments; they are not implemented features.
