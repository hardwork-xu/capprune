# Contributing

[简体中文](CONTRIBUTING_zh.md) · [Maintainer conventions](AGENTS.md) · [Development](docs/en/DEVELOPMENT.md)

I prefer small, reviewable changes tied to an observed correctness issue, a measured bottleneck, or a clearly stated user need. The core remains a CPU exact-search library; a new backend or service needs its own scope and evidence.

Use Python 3.12 and uv 0.8.22 from the project root:

```sh
uv sync --frozen
make demo
make check
make build
```

After dependencies are installed, the default tests and demonstration run offline. `make check` runs formatting, lint, type checks, tests, and documentation checks. For a measurement change, also run:

```sh
uv run python benchmark.py --output results/new.json
uv run python scripts/analyze.py results/new.json
```

Use a fresh result filename for each run; retain valid unfavorable samples and failure records. Preserve the original frozen protocol. A changed protocol needs a new file, rationale, and results identified as a separate experiment. Never replace a target with a measured value or extrapolate a CPU result to another backend.

A complete contribution includes a reproducible trigger or motivation, relevant tests exercising real computation, updated English and Simplified Chinese API/CLI/documentation text, and validation commands with their actual status. Changes to bounds, normalization, ties, layout, or persistence need corresponding correctness tests. Performance changes need the same precision, thread count, workload, and timing scope on both paths. Keep identifiers and machine-readable keys in English.

Use a Conventional Commits English summary and a Chinese body describing the change and verification. Preserve existing contributor attribution and third-party notices. Contributions to project-owned code are under the [MIT license](LICENSE); do not include material whose license is incompatible or unclear.

Keep datasets, credentials, private logs, absolute personal paths, and local Git identity metadata out of public artifacts. Inspect both file content and commit author/committer metadata before publishing history. The public source archive intentionally excludes `.git`; the private local history is maintained separately. Do not reset history, modify remotes, publish, or deploy as an incidental part of a fix.

For security concerns, follow [SECURITY.md](SECURITY.md). No public issue tracker or private reporting address is configured in this local release; do not invent one in documentation or place sensitive reports in a public channel.
