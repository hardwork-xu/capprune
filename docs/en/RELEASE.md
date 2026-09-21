# Release preparation: 0.1.0

[简体中文](../zh/RELEASE.md) · [Home](../../README.md) · [Third-party notices](../../NOTICE.md)

I am preparing CapPrune as a maintainable, publicly shareable source project with explicit evidence limits. The public source repository is [hardwork-xu/cosine-vector-search](https://github.com/hardwork-xu/cosine-vector-search). These version 0.1.0 release notes remain a draft; source publication does not imply a hosted GitHub release, package-registry publication or hosted service.

## Installation and demonstration

Use Python 3.12 and uv 0.8.22. The locally validated platform is macOS arm64 CPU. Clone the repository and run:

```sh
git clone https://github.com/hardwork-xu/cosine-vector-search.git
cd cosine-vector-search
uv sync --frozen
make demo
make check
uv run python benchmark.py --output results/new.json
uv run python scripts/analyze.py results/new.json
make build
```

The lockfile fixes package versions and download hashes. Installation may need network access; the default demo and tests run offline after installation. Use a new result filename for each experiment. `make build` produces a wheel and source distribution under `dist/`; a local build is not a package-registry publication. Run `uv run capprune --help` for the bilingual CLI.

Evidence entry points: [acceptance checks](../../results/acceptance/checks.json), [raw benchmark](../../results/reference.json), [generated summary](../../results/analysis/summary.json), [benchmark chart](../../results/analysis/benchmark.png), and [frozen protocol](../../configs/protocol.json). Expected package filenames are `dist/capprune-0.1.0-py3-none-any.whl` and `dist/capprune-0.1.0.tar.gz`; the acceptance record states whether the actual build succeeded.

The Docker path is intended for Linux CPU with the pinned Python base image and locked runtime dependencies:

```sh
docker build -t capprune:0.1.0 .
docker run --rm capprune:0.1.0
```

The original macOS host had no Docker, so its archived local acceptance record remains unchanged. [Public Ubuntu 24.04 CI](https://github.com/hardwork-xu/cosine-vector-search/actions/runs/35602650743) has now passed all 70 tests, static/type checks, package build, benchmark smoke, plotting, Docker build and container demo. [Publication evidence](../../results/publication.json) records the tested public snapshot. This validates the Linux execution path, not full Linux benchmark performance.

## Release notes draft

CapPrune 0.1.0 introduces an immutable float64 cosine top-k index with spherical-cap block pruning, a contiguous scan baseline, and a pruning-disabled block path. It includes deterministic row-ID ties, bounded assignment scratch space, input validation, NPZ persistence, a Python API, bilingual CLI, offline example, tests, and a frozen benchmark protocol. English and Simplified Chinese documentation share the same implementation and evidence.

Performance claims must use the generated tables and raw records described in [EXPERIMENTS.md](EXPERIMENTS.md), including slower cases. The project does not claim a new geometric algorithm, superiority over Faiss, GPU acceleration, production deployment, or model inference acceleration. The current benchmark measures complete single-query library calls, not end-to-end embedding generation or an application.

Known limits: index building costs O(I N C d); two float64 vector layouts occupy 16Nd bytes before overhead; broad caps and small inputs can lose to scanning; the index has no online updates; numerical agreement is validated on the declared host rather than formally certified across all floating-point runtimes.

The macOS benchmark requests one Accelerate thread through `VECLIB_MAXIMUM_THREADS=1` before NumPy import. Effective Accelerate thread count cannot be directly inspected through `threadpoolctl` here; use “one thread requested” when describing these results.

## Public presentation text

**One-line introduction / GitHub About:** Auditable exact cosine search on CPU with spherical-cap block pruning, reproducible benchmarks, and bilingual documentation.

**Suggested Topics:** `vector-search`, `cosine-similarity`, `branch-and-bound`, `numpy`, `cpu`, `benchmark`, `reproducible-research`, `python`.

**Descriptive citation:** CapPrune: exact cosine retrieval with spherical-cap block pruning, version 0.1.0 (2026), software. Record the source revision or artifact hash used. Include the public repository URL: https://github.com/hardwork-xu/cosine-vector-search. No DOI has been assigned. A descriptive citation is provided without adding personal author metadata; no `CITATION.cff` is supplied.

## Artifact and publication boundary

The publication-ready source bundle must contain project-owned source, tests, configuration, bilingual documents, licenses, and sanitized experiment evidence. Exclude `.git`, virtual environments, caches, private reports, downloaded dependency artifacts, and local machine identity. Standard build outputs under `dist/` are separate from that source bundle.

The public repository starts with a sanitized source snapshot under the verified public account `hardwork-xu`. Original local history remains separate and is not rewritten or pushed. Local commit IDs in the development record, benchmark and acceptance files remain historical provenance references; they cannot be resolved on the public remote. Per-file SHA-256 values preserve the connection between the published numerical core and the measured implementation. Supporting publication files may differ without changing the original benchmark.

The public GitHub repository has been created. Public CI passed as recorded above; [Actions](https://github.com/hardwork-xu/cosine-vector-search/actions) reports later runs. The archived local acceptance file is not a remote CI report. Package-registry publication, a hosted GitHub release, DOI assignment and service deployment remain unperformed. Preserve the original experiment records when publishing or validating later changes.
