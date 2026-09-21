# Code walkthrough and maintenance

[简体中文](../zh/WALKTHROUGH.md) · [Home](../../README.md) · [API](ARCHITECTURE.md)

## Start with a running example

After installing the project, run:

```sh
.venv/bin/python -m capprune demo
.venv/bin/python examples/demo.py
.venv/bin/python -m pytest -q tests/test_cli.py
```

The two demo commands use the same implementation in [`cli.py`](../../src/capprune/cli.py). The demonstration generates 4,096 synthetic vectors in 32 dimensions around 16 random centers, builds a real index, searches 16 synthetic queries, and compares the ordered top-10 results with a real contiguous scan. Read `dataset_kind`, `exact_match`, `max_absolute_score_error`, and `evaluated_fraction` together. Fewer evaluated vectors are evidence of pruning, not automatically evidence of lower latency. Timing evidence comes from [`benchmark.py`](../../benchmark.py) under the frozen protocol.

## Follow the public call chain

1. [`__main__.py`](../../src/capprune/__main__.py) calls `cli.main()`. The installed `capprune` command reaches the same function through the package entry point.
2. `_parser()` checks command syntax. `_load_array()` loads `.npy` without pickle. `main()` calls `CapIndex.build()`, `CapIndex.load()`, or `index.search()`, then emits JSON with English machine fields.
3. [`index.py`](../../src/capprune/index.py) validates inputs and performs every numerical operation. `SearchResult` exposes read-only result arrays and counters.
4. CLI JSON serialization does not approximate or recompute scores. Expected argument, file, and numerical input errors return status 2. Unexpected implementation defects remain visible as failures.

The CLI prevents an output path from replacing an input path. Query JSON uses a same-directory temporary file and replacement; failed writes clean up the temporary file. Parent directories must exist. The core index's `save()` also uses temporary-file replacement, while `load()` reconstructs geometry instead of trusting persisted bounds.

## Understand construction before optimizing search

`_normalize()` converts real numeric inputs into owned float64 arrays. It first divides each row by its largest absolute component, then divides by its norm. Directly squaring a very large finite input can overflow; directly squaring a subnormal input can underflow. Scaling avoids both without changing the intended direction. Zero rows, NaN, infinity, unsupported dtypes, or invalid shapes are rejected.

`CapIndex.build()` chooses initial centers using the seeded random generator. Each Lloyd round computes nearest-center assignments by maximal cosine score and then normalizes cluster sums. The score matrix is evaluated in row chunks bounded by `max_matrix_bytes`. Empty or exactly cancelled centers retain their previous direction during iterations. Final labels are compacted into nonempty blocks. Correctness requires a partition; it does not require globally optimal clustering.

`CapIndex.__init__()` stably sorts labels, stores original row IDs in `_order`, constructs block slices from `_offsets`, and packs vectors into `_blocked`. It derives each block's center and minimum center/member cosine from the actual members. `_cap_min` is widened outward using the numerical margin. These members, centers, and caps must stay consistent for the life of the immutable index.

When modifying construction, verify that every row appears exactly once, no original ID is lost, all stored vectors and centers meet the normalization contract, and every cap covers every member. A narrower-looking cap is not a valid optimization if it excludes even one member.

## Map the mathematical bound to code

`CapIndex._bounds(query)` computes `a = center @ query` for each block, widens it conservatively, and compares it with `s = _cap_min`. The implementation mirrors the formula in [RESEARCH.md](RESEARCH.md):

- If `a >= s`, the query direction lies inside the cap, so the upper bound is 1 before numerical slack.
- Otherwise, the bound is `a*s + sqrt(1-a*a)*sqrt(1-s*s)` with a numerically guarded form of the products.
- The final upward adjustment and `nextafter(..., +inf)` keep rounding on the conservative side.

The inside-cap branch is essential. Applying the boundary formula to all inputs would underestimate the bound for some queries. Widening only the final score by a tiny epsilon is also insufficient near cosine ±1, where square-root sensitivity matters. The implementation's practical float64 agreement contract is tested; it is not a formally verified interval-arithmetic implementation for every platform.

## Read traversal and selection together

`search()` validates `k` and mode, normalizes the query array, allocates result arrays, and processes queries sequentially. `scan` computes all scores in original order. `blocked` visits every packed block. `pruned` computes and sorts upper bounds, then scores only visited blocks.

`_topk()` uses partial selection to find the cutoff, retains all cutoff ties, then sorts the retained candidates by descending score and ascending original ID. In the block paths it merges the previous best candidates with the actual scores from the next block. Only a strict `upper[block] < best_scores[-1]` permits termination, and only after the best list has length `k`. Changing this comparison to `<=` can lose a tied result with a smaller original ID.

The counters make two failure modes distinguishable. High `evaluated_vectors` means the geometry did not prune much. Low `evaluated_vectors` with poor elapsed time means bounds, dispatch, or repeated selection outweighed the saved dot products. Compare against `blocked` to isolate pruning from packed block traversal overhead. All three modes use the same score precision and top-k routine.

## Persistence and ownership

`save()` records schema, normalized original vectors, labels, and build configuration. `load()` checks the schema and array properties, validates contiguous nonnegative labels, and passes the validated members through construction to regenerate centers and certificates. Editing an NPZ certificate cannot trick traversal because certificates are not stored. An NPZ can still require excessive decompression memory, so size-untrusted uploads are outside the interface's security scope.

Input arrays are copied; the index stores no query history. Public arrays are read-only, and metadata is copied on access. Scratch arrays are local to a call. No explicit close method is required because search holds no open files or external device resources. Python reference lifetime governs arrays; array byte counts and process RSS remain different metrics.

## Debug and verify changes

```sh
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m mypy src/capprune
.venv/bin/python -m capprune demo --vectors 256 --dimension 12 --clusters 8 --queries 7 --k 5
```

For a numerical mismatch, retain the seed and exact input first. Compare `scan`, `blocked`, and `pruned` on the same index. If only `pruned` disagrees, inspect each skipped block's bound against its true maximum score. If `blocked` also disagrees, inspect packing, original IDs, top-k ties, and dense-kernel score differences. Inspect private arrays only during development; they are not a supported external API.

For a slowdown, measure work counters and latency separately, then inspect the full raw samples rather than the best repetition. Do not change a frozen target after seeing results. For a persistence failure, reproduce it with a copy of the archive and run the load tests; do not bypass schema or norm validation just to make a file load.

The default tests execute real numerical code and subprocess CLI calls offline. Hardware support, remote CI success, production relevance, and formal floating-point guarantees must not be inferred from those tests. The validated environment and actual experiment outcomes are in [EXPERIMENTS.md](EXPERIMENTS.md); actual development changes and verification history are in [DEVELOPMENT.md](DEVELOPMENT.md).
