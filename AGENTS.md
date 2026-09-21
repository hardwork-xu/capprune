# Maintainer conventions / 维护约定

- Core: `src/capprune/index.py`; interface: `cli.py`; experiments: `benchmark.py`, `scripts/analyze.py`; paired documents: `docs/en`, `docs/zh`.
- Install / 安装: `uv sync --frozen`. Python 3.12; use uv 0.8.22. Run / 运行: `uv run capprune demo`.
- Checks / 检查: `make check`; experiments / 实验: `make benchmark`; packaging / 构建: `make build`.
- Keep English and Simplified Chinese documentation, CLI explanations, API contracts and statuses aligned. 同步维护中英说明，机器字段仅用英文。
- Preserve `configs/protocol.json` and all valid raw samples. Changed protocols require a new file and an explicit rationale. 实验前冻结协议；不得覆盖不利结果或把目标写成实测。
- Raw evidence must identify source hashes, command, UTC time, seed, hardware, dependency versions, status and all samples. Distinguish logical array bytes, RSS and theoretical bounds. 记录源码与环境，不混用内存口径。
- Never commit credentials, absolute private paths, personal records, downloaded dependencies or fabricated identities. 不推送、公开发布、部署或改写历史，除非获得明确授权。
- Done means affected tests, lint, typing, package build, bilingual/link checks and evidence are current. 完成须重跑受影响验证并保留真实证据。
