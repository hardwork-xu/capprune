# Security and operational limits

[简体中文](SECURITY_zh.md) · [Architecture](docs/en/ARCHITECTURE.md)

CapPrune 0.1.0 is a local CPU library and CLI, not a hosted service or a security boundary. No authentication, tenant isolation, encryption, or production service-level commitment is provided. Python 3.12 on macOS arm64 CPU is the locally validated configuration; other platforms need their own verification.

Use trusted numeric inputs and trusted index archives. Rejecting malformed arrays and avoiding pickle deserialization do not make a compressed NPZ parser a sandbox: sufficiently large or hostile input can exhaust memory, CPU time, or disk space. Apply operating-system limits when processing externally supplied files. The clustering assignment budget limits one scratch allocation, not total memory; original and packed float64 data occupy roughly 16Nd bytes before other arrays and runtime allocations.

An index preserves numeric vectors and original row IDs. It does not anonymize or encrypt them. Do not publish an index built from private inputs. File paths and diagnostic output can also reveal local context; inspect logs before sharing. Saving output requires normal filesystem permissions and should use a dedicated destination rather than an unrelated existing file.

The pruning proof assumes normalized real vectors. Numerical guards and consistency tests provide the documented float64 behavior; they do not constitute a formal proof for every floating-point platform. Untrusted changes to stored bounds or layout can undermine correctness, so persistence checks are part of the supported loading path. See [RESEARCH.md](docs/en/RESEARCH.md) for the exactness boundary and [EXPERIMENTS.md](docs/en/EXPERIMENTS.md) for measured scope.

Only the current 0.1.x code line is in scope for maintenance; there is no guaranteed response time. This local release has no configured public repository or verified private security contact. Preserve a minimal reproduction locally, remove private data, and use a maintainer-approved private contact once one is published. Do not assume an unlisted address exists or post exploit details containing private information publicly.

Before public release, review tracked files, generated artifacts, dependency notices, and commit author/committer identities. Source bundles exclude `.git`; private local Git metadata must remain separate unless explicitly reviewed for publication. A clean source archive does not make an unreviewed historical Git push safe.
