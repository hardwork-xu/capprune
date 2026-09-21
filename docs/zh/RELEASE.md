# 发布准备：0.1.0

[English](../en/RELEASE.md) · [主页](../../README_zh.md) · [第三方声明](../../NOTICE_zh.md)

我将 CapPrune 整理为可持续维护、可公开分享、证据边界明确的源码项目。公开源码仓库为 [hardwork-xu/capprune](https://github.com/hardwork-xu/capprune)。以下 0.1.0 发布说明仍是草稿；公开源码不代表已经创建托管 GitHub release、发布到软件包平台或提供托管服务。

## 安装与演示

使用 Python 3.12 和 uv 0.8.22。本地验证平台为 macOS arm64 CPU。克隆仓库并执行：

```sh
git clone https://github.com/hardwork-xu/capprune.git
cd capprune
uv sync --frozen
make demo
make check
uv run python benchmark.py --output results/new.json
uv run python scripts/analyze.py results/new.json
make build
```

锁文件固定软件包版本与下载哈希。安装可能需要网络；依赖安装后默认演示与测试可离线运行。每次实验使用新的结果文件名。`make build` 在 `dist/` 下生成 wheel 和源码分发包，本地构建不等于发布到软件包平台。运行 `uv run capprune --help` 查看双语 CLI。

证据入口：[验收记录](../../results/acceptance/checks.json)、[原始基准](../../results/reference.json)、[生成摘要](../../results/analysis/summary.json)、[基准图表](../../results/analysis/benchmark.png)、[冻结协议](../../configs/protocol.json)。预期软件包文件名为 `dist/capprune-0.1.0-py3-none-any.whl` 和 `dist/capprune-0.1.0.tar.gz`；实际构建是否成功以验收记录为准。

Docker 路径面向 Linux CPU，使用固定 Python 基础镜像版本和锁定运行依赖：

```sh
docker build -t capprune:0.1.0 .
docker run --rm capprune:0.1.0
```

原始 macOS 主机没有 Docker，其本地验收档案保持不变。[公开 Ubuntu 24.04 CI](https://github.com/hardwork-xu/capprune/actions/runs/35602650743) 现已通过全部 70 项测试、静态/类型检查、包构建、基准冒烟、绘图，以及 Docker 构建和容器演示。[公开发布证据](../../results/publication.json)记录被验证的公开源码快照。这证明 Linux 执行路径可运行，不是完整 Linux 性能基准结论。

## 发布说明草稿

CapPrune 0.1.0 提供不可变 float64 余弦 top-k 索引，包含球冠分块剪枝、连续扫描基线，以及关闭剪枝的分块路径。功能包括按原始行号确定性处理同分、受限分配临时空间、输入验证、NPZ 持久化、Python API、双语 CLI、离线示例、测试，以及冻结的基准协议。英文和简体中文文档共享同一套实现与证据。

性能声明必须引用 [EXPERIMENTS.md](EXPERIMENTS.md) 中说明的自动生成表格和原始记录，并保留较慢场景。项目不宣称新几何算法、优于 Faiss、GPU 加速、生产部署或模型推理加速。当前基准测量完整的单查询库调用，不包含嵌入生成或应用端到端流程。

已知限制：索引构建成本为 O(I N C d)；两份 float64 向量布局在额外开销前占 16Nd 字节；较宽球冠和较小输入可能比扫描更慢；索引不支持在线更新；数值一致性在声明的主机上验证，并非对所有浮点运行时给出形式化认证。

macOS 基准在导入 NumPy 前通过 `VECLIB_MAXIMUM_THREADS=1` 请求一个 Accelerate 线程。当前环境无法用 `threadpoolctl` 直接检查 Accelerate 实际线程数，描述结果时应写“请求一个线程”。

## 公开介绍文案

**一句话介绍 / GitHub About：** 面向 CPU 的可审阅精确余弦检索，提供球冠分块剪枝、可复现基准实验与中英双语文档。

**建议 Topics：** `vector-search`、`cosine-similarity`、`branch-and-bound`、`numpy`、`cpu`、`benchmark`、`reproducible-research`、`python`。

**描述性引用：** CapPrune：基于球冠分块剪枝的精确余弦检索，版本 0.1.0（2026），软件。记录使用的源码 revision 或产物哈希。附公开仓库地址：https://github.com/hardwork-xu/capprune。尚未分配 DOI。提供描述性引用而不增加个人作者元数据，不附 `CITATION.cff`。

## 产物与发布边界

可公开源码归档应包含项目自有源码、测试、配置、双语文档、许可证，以及去除私人信息的实验证据。排除 `.git`、虚拟环境、缓存、私人报告、下载的依赖产物和本地机器身份。`dist/` 下标准构建产物与该源码归档分开提供。

公开仓库在已核验的公开账户 `hardwork-xu` 下，从经过脱敏的源码快照开始。原始本地历史独立保留，没有改写或推送。开发记录、基准和验收文件中的本地提交 ID 仍作为历史来源证据保留，不能在公开远端解析。逐文件 SHA-256 保留公开数值核心与实测实现之间的对应关系。发布配套文件可能发生变化，不会因此改写原始基准。

公开 GitHub 仓库已创建。首次 CI 执行情况需要在 [Actions](https://github.com/hardwork-xu/capprune/actions) 核验；归档的本地验收文件不是远端 CI 报告。软件包平台发布、托管 GitHub release、DOI 分配和服务部署仍未执行。发布或验证后续修改时，应保留原始实验记录。
