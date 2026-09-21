# 开发记录

[English](../en/DEVELOPMENT.md) · [代码导读](WALKTHROUGH.md) · [实验](EXPERIMENTS.md)

我用这份记录区分设计决策、实际修复与已验证结果。它描述下列提交对应的本地开发，不暗示更长的研究经历、生产部署或公开发表。

## 已记录的本地历史

以下条目读取自 `git log --format='%h %s'`，哈希对应真实原始本地提交。[公开仓库](https://github.com/hardwork-xu/capprune) 的历史独立起始于经过脱敏的源码快照，排除私人 Git 身份元数据。下列及原始证据中的本地哈希作为来源引用保留，不能在公开远端解析；原始历史没有被改写或发布。原始证据中的逐文件 SHA-256 可用于检查公开数值核心与冻结协议和实测文件一致。

| 提交 | 实际摘要 | 该阶段完成的工作与验证 |
|---|---|---|
| `ad99556` | `chore: freeze scope and benchmark acceptance protocol` | 检查空工作区与可用 CPU 环境；在性能测量前固定范围、工作负载、基线、分数容差及 1.5 倍/30% 目标。Docker 不可用。 |
| `1a2edab` | `build: add locked CPU environment and container recipe` | 生成并安装依赖锁，增加构建任务、CI 配置与 CPU 容器配置。隔离环境成功导入 NumPy 2.2.6 和 scikit-learn 1.7.2。未执行容器或远端 CI 检查。 |
| `05e415c` | `feat: implement guarded spherical-cap cosine search` | 增加聚类、保守上界、稳定 top-k、扫描/分块/剪枝模式，以及原子 NPZ 持久化。49 项核心测试通过，覆盖数值边界、非法输入、并发读取、损坏归档与写入失败恢复；核心静态与类型检查通过。 |
| `784de7d` | `feat: expose bilingual offline CLI and reusable examples` | 增加演示、建库、查询命令，提供双语帮助与结构化 JSON。17 项 CLI 子进程测试通过，覆盖持久化往返和输出保护；类型检查通过。 |
| `0f8260d` | `perf: add fair baselines and reproducible benchmark evidence` | 增加随机顺序重复测量、完整样本保留、失败处理、原子结果写入与自动分析。在正式运行前移除不必要的查询分配，并配置 Accelerate 线程请求。完整 70 项测试、Ruff 与 mypy 通过。 |

这些条目之后可能还有文档或验收提交。机器可读的[验收记录](../../results/acceptance/checks.json) 标识实际验证的源码快照，不能假设较早检查自动覆盖后续每项修改。

## 实际发现的问题与修复

| 观察到的问题 | 分析与已实现的修改 | 验证 / 影响 |
|---|---|---|
| 早期 editable 安装无法导入 `capprune`。 | 当时安装环境早于源码包落盘；重新构建 editable 安装后，完整源码包可被导入。 | 后续 API 导入、CLI 子进程测试和干净环境验收覆盖安装后的包。该安装失败没有被计作算法失败。 |
| 自定义 argparse 错误路径未通过类型检查。 | 解析器的错误处理不会返回，重写方法需要与该控制流一致的 `Never` 返回类型。 | 修正标注后 mypy 通过；真实子进程测试覆盖非法 CLI 输入。 |
| pyparsing 3.3.3 导致绘图依赖兼容性警告。 | 开发环境固定 pyparsing 3.2.3，并重新生成实际锁文件；没有通过屏蔽警告或削弱断言让检查通过。 | 修改后的锁定环境生成图表时不再产生该兼容性警告。固定版本是环境修复，不是性能成果。 |
| 未使用原子替换时，索引写入失败可能留下不完整目标文件。 | 保存索引时，在目标目录写临时文件、flush 和 fsync，然后原子替换目标；失败时清理临时文件。 | 核心测试验证异常传播、临时文件清理和已有目标保留。加载禁用 pickle、校验字段，并重建球冠信息而非信任已保存上界。 |
| `threadpoolctl` 显示 libomp，但不能检查 NumPy 实际使用的 Apple Accelerate BLAS 运行时。 | NumPy 构建元数据确认后端为 Accelerate。导入 NumPy 前请求 `VECLIB_MAXIMUM_THREADS=1`，同时设置 OpenBLAS/OMP 选项。 | 原始证据记录后端与检查限制，证明配置请求相同，而不是已直接验证 Accelerate 实际线程数。 |
| 即使只扫描极少向量，剪枝路径仍分配全部 N 个原始行号。 | 将完整 `arange(N)` 分配限制在真正需要它的扫描路径，分块路径复用已保存的排列。 | 核心测试通过。该修复发生在正式基准前；冻结的工作负载、基线、目标和容差均未改变。 |
| 基准后续出错可能丢弃同一场景此前已完成的有效样本。 | 测量框架在场景进度记录中保留累计样本并显式报告失败，结果采用原子替换写入。 | `test_failure_preserves_completed_samples` 在真实搜索完成若干次后注入错误，检查正耗时有效样本仍保留。正式基准没有失败场景。 |

相关实现见[核心](../../src/capprune/index.py)、[CLI](../../src/capprune/cli.py)、[基准脚本](../../benchmark.py)与[测试](../../tests/test_benchmark.py)。没有为了性能结果调整冻结协议。初步冒烟验证与完整正式测量分别记录，前者不能替代后者。

## 正式测量与结论变化

正式运行的 run_id 为 `140ea5bb-9c95-4e8a-b2ab-17bcde0903ca`；框架记录开始时间为 `2026-09-21T12:20:21.157225+00:00`，结束时间为 `2026-09-21T12:20:31.138783+00:00`。源码 revision 为 `0f8260de8bd9de459de4d5f63cd86fb81cf08aca`，聚合源码 SHA-256 为 `cd50eb987f9d56f1a1e778a5b41127097aeb0115ccb52787ec05c862aec8c530`。这些时间只描述该次测量，不是总开发时长。

[原始文件](../../results/reference.json) 包含 **5,880** 个有效样本：7 个场景 × 3 种模式 × 40 个查询 × 7 轮重复。每个场景均通过有序行号与分数检查，观察到的最大分数绝对误差为 `4.440892098500626e-16`。[自动分析](../../results/analysis/summary.json) 显示，在有利的 50,000×64 聚类合成输入上，相对相同 float64 扫描，主要场景中位延迟加速 **10.20 倍**，平均实际计算向量比例为 **2.34%**。真实数字数据上的剪枝加速比仅为 **0.23 倍**，各向同性与极小输入也比扫描慢。所有有效测量均保留在同一结果文件中。

由此能够得到的结论，是在所记录 CPU 配置下，对紧凑聚类数据实现选择性加速，而不是普遍的检索性能优势。不利场景说明需要分析球冠选择性与遍历开销，并推动后续自适应回退研究；不能据此在看到结果后修改验收目标。

## 重新验证这份记录

在项目根目录执行：

```sh
uv sync --frozen
make check
uv run python scripts/validate_results.py results/reference.json
uv run python scripts/analyze.py results/reference.json
make build
uv run python scripts/verify.py
```

最终验证器将命令、退出状态、脱敏日志和源码快照写入 [checks.json](../../results/acceptance/checks.json)。后续验证支持文件或文档变化可能使源码快照与较早基准聚合哈希不同，逐文件哈希可用于核验核心和协议是否改变。不得把旧结果重新标记为修改后数值代码的测试结果。

归档的本地验收中，Docker 构建/运行和远端 GitHub Actions 均为 **not run**：当时 Docker 不可用，源码也尚未公开。此后公开仓库已创建，当前远端执行记录见 [Actions](https://github.com/hardwork-xu/capprune/actions)，与该历史文件分别记录。创建配置文件不等于执行证据。软件包平台发布、托管 GitHub release 和部署仍未执行，见 [RELEASE.md](RELEASE.md)。

## 源码包隐私检查

本地包内容审计发现，首次源码分发包包含指向私人本地元数据的 `.git` 控制文件。在 `.gitignore` 明确排除 `.git` 并重新构建后，重复包审计通过。该次原始本地审计期间没有上传任何软件包或源码压缩包。此打包修改不改变已测搜索实现或冻结基准。
