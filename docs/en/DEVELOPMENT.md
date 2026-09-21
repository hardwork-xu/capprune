# Development record

[简体中文](../zh/DEVELOPMENT.md) · [Walkthrough](WALKTHROUGH.md) · [Experiments](EXPERIMENTS.md)

I keep this record to separate design decisions, actual fixes, and verified outcomes. It describes the local development represented by the commits below; it does not imply a longer research history, production deployment, or publication.

## Recorded local history

The following entries were read from `git log --format='%h %s'`. Commit hashes identify real original local history. The [public repository](https://github.com/hardwork-xu/cosine-vector-search) starts separately with a sanitized source snapshot that excludes private Git identity metadata. The local hashes below and in raw evidence are preserved provenance references and cannot be resolved on the public remote; the original history was not rewritten or published. Per-file SHA-256 values in the raw evidence allow checking that the public numerical core and frozen protocol match the measured files.

| Commit | Actual summary | Completed work and verification at that stage |
|---|---|---|
| `ad99556` | `chore: freeze scope and benchmark acceptance protocol` | Inspected the empty workspace and available CPU environment; fixed scope, workloads, baseline, score tolerances, and 1.5×/30% targets before performance measurements. Docker was unavailable. |
| `1a2edab` | `build: add locked CPU environment and container recipe` | Generated and installed the dependency lock; added build tasks, CI configuration, and the CPU container recipe. NumPy 2.2.6 and scikit-learn 1.7.2 imported in the isolated environment. Container and remote CI checks were not run. |
| `05e415c` | `feat: implement guarded spherical-cap cosine search` | Added clustering, guarded bounds, stable top-k, scan/block/pruned modes, and atomic NPZ persistence. 49 core tests passed, including numeric boundaries, invalid inputs, concurrent reads, corrupted archives, and failed-save recovery; core lint/type checks passed. |
| `784de7d` | `feat: expose bilingual offline CLI and reusable examples` | Added demo, build, and query commands with bilingual help and structured JSON. 17 subprocess CLI tests passed, including persistence round trips and output protection; type checks passed. |
| `0f8260d` | `perf: add fair baselines and reproducible benchmark evidence` | Added randomized repeated measurement, complete sample retention, failure handling, atomic result writes, and generated analysis. Removed avoidable query allocation and configured Accelerate thread requests before the formal run. The complete 70-test suite, Ruff, and mypy passed. |

Later documentation or acceptance commits may follow these entries. The machine-readable [acceptance record](../../results/acceptance/checks.json) identifies the source snapshot actually verified, rather than assuming the earlier checks cover every later edit.

## Problems found and changes made

| Observation | Diagnosis and implemented change | Verification / consequence |
|---|---|---|
| An early editable install could not import `capprune`. | The environment was installed before the source package existed; rebuilding the editable installation made the completed source package available. | Subsequent API imports, CLI subprocess tests, and the clean-environment acceptance path exercise the installed package. This installation failure was not counted as an algorithm failure. |
| The custom argparse error path failed type checking. | The parser's error handler does not return; its override needed a `Never` return annotation matching that control flow. | mypy passed after correcting the annotation; invalid CLI input is exercised through real subprocesses. |
| Plotting emitted dependency compatibility warnings with pyparsing 3.3.3. | The development environment pins pyparsing 3.2.3; the actual lock was regenerated. No warning suppression or weakened test assertion was used to make a check pass. | The resulting locked environment supports plot generation without that compatibility warning. The pin is an environment repair, not a performance result. |
| A failed index write could leave a partial target without atomic replacement. | Index saving writes a temporary file in the destination directory, flushes and fsyncs it, then atomically replaces the target. The temporary file is cleaned on failure. | Core tests verify failure propagation, temporary-file cleanup, and preservation of an existing target. Loading disables pickle, validates fields, and rebuilds cap information rather than trusting saved bounds. |
| `threadpoolctl` exposed libomp, but not NumPy's actual Apple Accelerate BLAS runtime. | NumPy build metadata identified Accelerate. `VECLIB_MAXIMUM_THREADS=1` is requested before importing NumPy, alongside OpenBLAS/OMP settings. | Raw evidence records the backend and the introspection limitation. It establishes equal requested configuration, not a directly verified effective Accelerate thread count. |
| The pruned path allocated all N original IDs even when almost no vectors were scanned. | The full `arange(N)` allocation was restricted to the scan path, which requires it. Blocked paths reuse the stored permutation. | Core tests passed. This repair happened before the formal benchmark; the frozen workloads, baseline, targets, and tolerances did not change. |
| A later benchmark error could otherwise discard valid earlier samples from the same case. | The harness preserves accumulated samples in the case's progress record and reports failures explicitly; result writes use atomic replacement. | `test_failure_preserves_completed_samples` injects an error only after actual searches and checks that completed positive-duration samples survive. No formal benchmark case failed. |

The source of these mechanisms is [the core](../../src/capprune/index.py), [CLI](../../src/capprune/cli.py), [benchmark](../../benchmark.py), and [tests](../../tests/test_benchmark.py). There were no performance-driven changes to the frozen protocol. Preliminary smoke validation is distinct from the complete measured run; it is not substituted for that run.

## Formal measurement and what it changed in the conclusion

The official run is `140ea5bb-9c95-4e8a-b2ab-17bcde0903ca`, started at `2026-09-21T12:20:21.157225+00:00` and finished at `2026-09-21T12:20:31.138783+00:00`, as recorded by the harness. Its source revision is `0f8260de8bd9de459de4d5f63cd86fb81cf08aca`; its aggregate source SHA-256 is `cd50eb987f9d56f1a1e778a5b41127097aeb0115ccb52787ec05c862aec8c530`. These timestamps describe this measurement, not total development duration.

The [raw file](../../results/reference.json) contains **5,880** valid samples: seven cases × three modes × 40 queries × seven repetitions. Every case passed ordered-ID and score checks, with maximum observed absolute score difference `4.440892098500626e-16`. [Generated analysis](../../results/analysis/summary.json) gives **10.20×** primary-case median speedup over the same float64 scan, with **2.34%** mean vector evaluation, on the favorable 50,000×64 clustered synthetic input. On the real digits case, pruned speedup was only **0.23×**; isotropic and tiny cases were also slower than scanning. All of those valid measurements remain in the same result file.

The resulting claim is selective acceleration for tight clustered data under the recorded CPU configuration. It is not a general retrieval performance claim. The unfavorable cases support the need to understand cap selectivity and traversal overhead, and motivate future adaptive fallback research. They do not justify changing the acceptance target after observing the outcome.

## Rechecking this record

From the project root:

```sh
uv sync --frozen
make check
uv run python scripts/validate_results.py results/reference.json
uv run python scripts/analyze.py results/reference.json
make build
uv run python scripts/verify.py
```

The final verifier records commands, exit statuses, sanitized logs, and a source snapshot in [checks.json](../../results/acceptance/checks.json). The source snapshot may differ from the earlier benchmark aggregate after supporting verification/documentation changes; per-file hashes permit checking whether the tested core and protocol changed. A result must not be relabeled as testing changed numerical code.

In the archived local acceptance run, Docker build/run and remote GitHub Actions are **not run**: Docker was unavailable and source publication had not yet occurred. The public repository has since been created; current remote execution is recorded in [Actions](https://github.com/hardwork-xu/cosine-vector-search/actions), independently of this historical file. Creating configuration files is not execution evidence. Package-registry publication, a hosted GitHub release and deployment remain unperformed, as documented in [RELEASE.md](RELEASE.md).

## Source-archive privacy check

A local package-content audit found that the source distribution initially included the `.git` control file, which points to private local metadata. Adding an explicit `.git` exclusion to `.gitignore` and rebuilding removed it; the repeated package audit passed. No package or source archive was uploaded during that original local audit. This packaging change does not change the tested search implementation or frozen benchmark.

## Public source and CI verification

Public snapshot `04ff43063be3cdc353bb0582444742da39be4f6d` passed [GitHub Actions](https://github.com/hardwork-xu/cosine-vector-search/actions/runs/35602650743) on Ubuntu 24.04: 70 tests, static/type checks, wheel/sdist build, benchmark smoke, analysis and Docker build/run. Anonymous repository and README requests returned HTTP 200; README bytes matched that snapshot. The source was published with the verified account’s privacy-preserving commit identity; original private history was not pushed. [Machine-readable evidence](../../results/publication.json) supplements the unchanged historical local records.
