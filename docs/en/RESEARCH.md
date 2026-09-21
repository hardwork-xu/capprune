# Research design and mathematical contract

[简体中文](../zh/RESEARCH.md) · [Home](../../README.md) · [Experiments](EXPERIMENTS.md)

## Positioning and choice

**CapPrune — exact cosine retrieval with spherical-cap block pruning** is a CPU research and engineering library for immutable, dense vector collections. I want an optimization whose work can be inspected: a skipped block should have a mathematical reason, and a slowdown should remain visible in the evidence. The intended users are engineers studying exact retrieval, researchers building correctness oracles for approximate indexes, and maintainers of modest local vector collections.

Three directions were considered against the inspected Apple M1 Pro host with 16 GiB unified memory, available CPU tools, unavailable Docker runtime, and unsuccessful model-host access:

| Direction | Research and engineering value | Feasibility and experiment cost | Decision |
|---|---|---|---|
| Speculative decoding | Distribution-preserving sampling, draft/target verification, and scheduling; established foundations in [Leviathan et al.](https://arxiv.org/abs/2211.17192). | Meaningful model-level evidence needs suitable model pairs and inference runtimes. Model downloads were not dependable in this environment. | Do not make model-scale claims from a sampling-only demonstration. |
| KV-cache allocation and reuse | Memory ownership, fragmentation, and serving concurrency; [PagedAttention](https://arxiv.org/abs/2309.06180) is an established reference. | A useful serving-level result needs integration into an inference engine and a representative device workload; that integration would dominate this delivery. | Outside this version. |
| Exact cosine retrieval | Geometric bounds, deterministic top-k, data layout, numerical reliability, and measurement against optimized dense computation. | Runs on the inspected CPU with no model download. Synthetic distributions expose mechanism limits; a bundled real numeric dataset adds a non-synthetic case. | Selected: one bound, one index, three comparable query modes. |

The scope is cosine top-k over finite, nonzero real vectors, normalized internally to float64. It is not arbitrary unnormalized maximum-inner-product search: normalizing vectors changes that problem. The current index is immutable. GPU kernels, approximate search, online insertion/deletion, sparse vectors, text embedding generation, a vector database service, and application-level relevance claims are non-goals.

## Prior work and contribution boundary

The sources below were accessed on 2026-09-21. The source list distinguishes an established idea from what this repository implements; it is not a claim to exhaustively survey the field.

| Primary source | What it establishes | Relationship to CapPrune |
|---|---|---|
| Ram and Gray, *Maximum Inner-Product Search using Tree Data-structures* (2012 [preprint](https://arxiv.org/abs/1202.6101)); published as *Maximum Inner-Product Search Using Cone Trees* ([author PDF](https://rithram.github.io/research/papers/2012/RG_KDD12.pdf)). | Inner-product branch-and-bound, angular cones, and ball/cone bounds. | Historical and mathematical foundation. CapPrune uses a flat block partition, not their single/dual-tree implementation. The angular bound is established geometry. |
| Dhillon and Modha, *Concept Decompositions for Large Sparse Text Data Using Clustering* (2001, [author PDF](https://www.cs.utexas.edu/~inderjit/public_papers/concept_mlj.pdf), [publication](https://doi.org/10.1023/A:1007612920971)). | Spherical k-means with normalized cluster centroids. | Source of the clustering approach, implemented here for dense arrays. Neither spherical k-means nor normalized centroids are new contributions. |
| Abuzaid et al., *To Index or Not to Index: Optimizing Exact Maximum Inner Product Search* ([preprint](https://arxiv.org/abs/1706.01449), [2019 author PDF](https://people.eecs.berkeley.edu/~matei/papers/2019/icde_optimizing_mips.pdf)). | Hardware-efficient dense computation can beat pruning indexes on some inputs; performance depends on workload. | Reason to retain a practical contiguous BLAS scan and report negative cases. This project does not reproduce MAXIMUS or OPTIMUS. |
| Faiss [index reference](https://github.com/facebookresearch/faiss/wiki/Faiss-indexes), [metric documentation](https://github.com/facebookresearch/faiss/wiki/MetricType-and-distances), and [library paper](https://arxiv.org/abs/2401.08281). | Flat inner-product search is exhaustive; cosine retrieval requires normalization; vector search remains an active systems problem. | Context and baseline design reference. Measured comparisons here use NumPy float64, not Faiss float32. No Faiss performance superiority is claimed. |

The contribution is a reviewable engineering realization: contiguous block storage, conservative floating-point bounds, deterministic row-ID ties, a pruning-disabled ablation, validated persistence, explicit resource controls, and reproducible evidence tying results to source. It is not a new geometric theorem, a new clustering algorithm, a complete literature reproduction, or a state-of-the-art claim. NumPy and its BLAS backend supply dense numerical kernels; CapPrune supplies partition construction, bound calculation, traversal, top-k orchestration, and the public execution contract.

## Research question and frozen acceptance

**Question:** When does conservative spherical-cap block pruning reduce single-thread CPU latency relative to a contiguous BLAS scan while preserving exact cosine top-k?

**Hypothesis:** Tight, separated clusters allow many entire blocks to be rejected. Isotropic high-dimensional data yields broad overlapping caps, while small collections leave too little vector work to amortize Python dispatch, bounds, and candidate merging. Increasing k can delay pruning. Build cost makes the mechanism most relevant when many queries reuse an index.

The machine-readable source of truth is [the premeasurement protocol](../../configs/protocol.json). These values are targets, not results:

| Class | Frozen statement |
|---|---|
| Target, primary | At least **1.5×** median single-query speedup over float64 contiguous scan on `clustered_n50000_d64`. |
| Target, secondary | At most **30%** mean evaluated-vector fraction on the same case. |
| Correctness acceptance | Identical ordered row IDs and scores within `atol=1e-12, rtol=1e-12` against scan on every evaluated workload. |
| Primary workload | 50,000 vectors, 64 dimensions, 64 generating clusters, Gaussian noise 0.035, k=10. |
| Measurement budget | Request one BLAS thread, seed 20260921, 40 queries per case, 7 repetitions, 4 warmup queries, 6 clustering iterations. |
| Coverage | Clustered 5k/50k vectors; 64/128 dimensions; k=10/100; isotropic 50k×64; real digits 1,757×64 with 40 held-out queries; 32×8 with k=N. |
| Functional acceptance | Importable API, all three search modes, stable ties, rejected invalid inputs, reusable/persistable index, offline demo, CLI, tests, locked build, and generated results. |

Measured outcomes belong in [EXPERIMENTS.md](EXPERIMENTS.md) and the raw result files. A target miss remains a target miss. The expected reduction in score evaluations is a mechanism hypothesis, not a guaranteed latency reduction.

The installed NumPy uses Apple Accelerate. `VECLIB_MAXIMUM_THREADS=1` is set before NumPy import, together with the OpenBLAS/OMP thread settings, to request the frozen single-thread configuration. `threadpoolctl` cannot directly introspect Accelerate's effective runtime thread count on this host; the evidence therefore establishes a **one-thread request**, not a verified effective thread count. Both paths use the same backend and settings. This limitation must accompany hardware-specific results.

## Mathematical definition

Let the collection contain N vectors in dimension d. Each nonzero input row is normalized to x_i with norm 1; the query is normalized to q. The requested answer contains k row IDs ordered by decreasing score

$$
f(i)=q^\top x_i,
$$

with ascending original row ID for equal computed scores. Let B be the number of nonempty blocks, and C the requested number of clustering centers. Spherical k-means assigns each row to a center maximizing inner product, then replaces each nonempty center by the normalized sum of its assigned rows. An empty or exactly cancelled sum retains the previous center during iterations; final zero-mean blocks use their first member as the cap direction. This is a partitioning heuristic; no global optimum is promised. Correctness does not depend on a good clustering objective: poor clusters only weaken pruning.

For a block j, select a unit center c_j and a lower bound

$$
s_j\leq\min_{i\in j}c_j^\top x_i.
$$

Every member lies in the closed spherical cap defined by c_j and s_j. Write a_j=q^\top c_j. An upper bound over that whole cap is

$$
U(a,s)=
\begin{cases}
1,&a\geq s,\\
as+\sqrt{\max(0,1-a^2)}\sqrt{\max(0,1-s^2)},&a<s.
\end{cases}
$$

For exact unit vectors the `max(0, ·)` wrappers are mathematically redundant. The implementation clips angular inputs to [−1, 1] and evaluates the algebraically equivalent, more stable factored square roots `sqrt((1-a)*(1+a))` and `sqrt((1-s)*(1+s))`.

### Why the bound holds

Set alpha=arccos(a) and theta=arccos(s), both in [0, pi]. A cap member has angle at most theta from its center. Angular triangle inequality therefore gives angle(q, x) at least max(0, alpha−theta). Cosine decreases on [0, pi], so the maximal possible score is at most cos(max(0, alpha−theta)). When alpha≤theta, the cap contains q and the maximum is 1. Otherwise, the cosine difference identity gives the second branch. This derivation specializes established angular branch-and-bound geometry; it does not depend on s being positive. A cap wider than a hemisphere is valid but often unhelpful. Applying the second branch when a≥s would be incorrect.

Visit blocks in decreasing U. Keep the best k candidates found so far. A block can be skipped only after k candidates exist and its conservative upper bound is **strictly less** than the current kth score. Equality must remain searchable because an unseen equal-scoring row may have a smaller row ID. Because subsequent blocks have no larger bound, traversal may stop when that strict condition holds. Every scanned block computes actual vector scores; no estimated score enters the result.

### Floating-point contract

The proof above is in real arithmetic. The implementation uses float64 normalization and dot products, widens s downward and a upward by `64 * eps * d`, then applies final outward slack and `nextafter` to the upper bound. Near ±1, square-root sensitivity makes a final tiny additive score epsilon alone inadequate; widening the cap and angular inputs addresses that failure mode. Scale-first normalization avoids overflow/underflow for finite extreme magnitudes. Zero vectors, NaN, infinity, dimensional mismatch, and invalid k are rejected explicitly.

The practical promise is exact search by this pruning algorithm with the stated float64 agreement tests. It is not a formal interval-arithmetic proof for every possible BLAS implementation and adversarial IEEE-754 input. A finite test suite cannot certify that stronger claim. Small arithmetic differences between dense kernels can also change the ordering of nearly equal mathematical scores; reported equality is relative to the common float64 baseline and declared tie rule. [The walkthrough](WALKTHROUGH.md) maps the formula and guards to the actual implementation.

## Invariants and complexity

The essential invariants are: every original row appears in exactly one nonempty block; its original row ID survives layout changes; all stored vectors and centers satisfy the normalization contract; each cap encloses its block with numerical slack; pruning never begins before k candidates exist; and all returned candidates have been scored explicitly. Persistence validation must reconstruct or check the information needed for those invariants instead of trusting arbitrary saved bounds.

For I clustering iterations, assignment costs O(I N C d). Score assignments are chunked to a configured byte budget; this bounds the assignment matrix scratch space, not total process memory. The index retains original and packed float64 vectors: **16Nd bytes** for these two arrays alone, plus O(N) row IDs/offsets, O(Bd) centers, and other arrays. This deliberate duplication makes the baseline and packed paths directly comparable but is not memory compression.

A query computes B bounds in O(Bd), orders them in O(B log B), and scores M≤N vectors in O(Md). `_topk` uses partial selection, retaining all cutoff ties before lexicographic sorting. For m candidates, cost is typically O(m+k log k), but all-tied input costs O(m log m). Across V visited blocks, typical selection/merge work is O(M+Vk log k); worst-case ties increase sorting work to O((M+Vk) log(N+k)). There is no sublinear worst-case guarantee: all blocks may be scanned, with selection overhead in addition to O(Nd). The explicit `blocked` mode visits the same layout without pruning, isolating the bound's effect from layout and per-block dispatch.

Expected build amortization, if the optimized query is faster, is

$$
Q_{\text{break-even}}\approx T_{\text{build}}/(T_{\text{scan}}-T_{\text{pruned}}).
$$

This conditional estimate charges the complete index build, including normalization, and does not subtract scan-only preparation cost; it is therefore conservative under those assumptions. It is undefined as a benefit when the denominator is nonpositive and must not be presented as a measured end-to-end application result. Concurrent throughput and large batched GEMM are separate workloads from the frozen one-query API experiment.

## What can be learned from a negative result

A low evaluated fraction combined with poor latency implies that bounds, top-k merging, or dispatch outweigh avoided matrix-vector work. A high evaluated fraction implies that partition geometry provides little selectivity. A strong synthetic result with weak real-data results limits the claim to the favorable distribution. A faster query with high build cost limits utility to reuse-heavy workloads. These outcomes are useful because each points to a different next question: tighter or hierarchical bounds, lower dispatch cost, adaptive scan fallback, memory-reduced storage, or a different partition objective. Those are future research questions, not implemented features.
