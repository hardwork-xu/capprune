# 代码导读与维护

[English](../en/WALKTHROUGH.md) · [主页](../../README_zh.md) · [API](ARCHITECTURE.md)

## 从可运行示例开始

安装项目后运行：

```sh
.venv/bin/python -m capprune demo
.venv/bin/python examples/demo.py
.venv/bin/python -m pytest -q tests/test_cli.py
```

两个演示命令使用 [`cli.py`](../../src/capprune/cli.py) 中的同一实现。演示在 16 个随机中心附近生成 4,096 个 32 维合成向量，构建真实索引，搜索 16 个合成查询，并将有序 top-10 与真实连续扫描比较。应一起阅读 `dataset_kind`、`exact_match`、`max_absolute_score_error` 与 `evaluated_fraction`。评估向量更少证明发生了剪枝，并不自动证明延迟更低。时间证据来自按冻结协议运行的 [`benchmark.py`](../../benchmark.py)。

## 沿公共调用链阅读

1. [`__main__.py`](../../src/capprune/__main__.py) 调用 `cli.main()`。安装后的 `capprune` 命令通过包入口到达同一函数。
2. `_parser()` 检查命令语法。`_load_array()` 禁用 pickle 加载 `.npy`。`main()` 调用 `CapIndex.build()`、`CapIndex.load()` 或 `index.search()`，随后输出使用英文字段的 JSON。
3. [`index.py`](../../src/capprune/index.py) 验证输入并执行全部数值操作。`SearchResult` 提供只读结果数组与计数器。
4. CLI 的 JSON 序列化不近似或重新计算分数。预期的参数、文件和数值输入错误返回状态 2。意料之外的实现缺陷仍作为失败暴露。

CLI 阻止输出路径覆盖输入路径。查询 JSON 通过同目录临时文件和替换操作写入，失败时清理临时文件，父目录须已存在。核心索引的 `save()` 同样使用临时文件替换；`load()` 重建几何信息，不信任持久化上界。

## 优化查询前先理解建库

`_normalize()` 将实数输入转换为自有 float64 数组。每行先除以最大绝对分量，再除以范数。直接平方有限大数可能溢出，直接平方次正规数可能下溢，预缩放避免这两种问题且不改变目标方向。零行、NaN、无穷、不支持的数据类型与非法形状会被拒绝。

`CapIndex.build()` 使用有种子的随机生成器选择初始中心。每轮 Lloyd 迭代通过最大余弦分数分配成员，再将各簇向量和归一化。分数矩阵按行分批，受 `max_matrix_bytes` 约束。空簇或向量和精确抵消的簇在迭代期间保留前一方向。最终标签压缩为非空分块。正确性依赖合法分区，不依赖聚类达到全局最优。

`CapIndex.__init__()` 稳定排序标签，用 `_order` 保留原始行 ID，通过 `_offsets` 建立分块切片，并将向量连续存储至 `_blocked`。每个块的中心及中心/成员最小余弦由实际成员计算。`_cap_min` 通过数值余量向外扩张。在不可变索引的整个生命周期中，成员、中心与球冠必须保持一致。

修改建库时，应确认每行恰好出现一次、原始 ID 没有丢失、所有已存向量与中心满足归一化约定，以及每个球冠覆盖全部成员。即使一个更窄的球冠看起来更有利，只要排除了一个成员，就不是合法优化。

## 将数学上界对应到源码

`CapIndex._bounds(query)` 为每块计算 `a = center @ query`，保守扩张后与 `s = _cap_min` 比较。实现对应 [RESEARCH.md](RESEARCH.md) 中的公式：

- 若 `a >= s`，查询方向位于球冠内，添加数值余量之前的上界为 1。
- 否则，上界为 `a*s + sqrt(1-a*a)*sqrt(1-s*s)`，代码用带数值保护的乘积形式计算。
- 最终向上修正及 `nextafter(..., +inf)` 使舍入保持保守方向。

球冠内部的分支不可省略。对全部输入使用边界公式，会低估部分查询的上界。仅给最终分数加一个很小的 epsilon 也不够，因为余弦接近 ±1 时平方根的敏感性很高。这里验证的是实用 float64 一致性约定，不是对所有平台完成形式验证的区间算术实现。

## 联合理解遍历与选择

`search()` 验证 `k` 和模式，归一化查询数组，分配结果数组，然后逐条处理查询。`scan` 按原始顺序计算全部分数。`blocked` 遍历全部连续分块。`pruned` 计算上界并排序，仅为访问到的块计算实际分数。

`_topk()` 用部分选择找到分数边界，保留所有边界并列项，再按分数降序、原始 ID 升序排序。在分块路径中，它把先前最优候选与下一个块的实际分数合并。只有 `upper[block] < best_scores[-1]` 严格成立，且当前候选列表已有 `k` 项时才可停止。将比较改为 `<=` 可能丢掉原始 ID 更小的并列结果。

计数器可以区分两种失败原因。`evaluated_vectors` 高，说明几何结构没能有效剪枝。`evaluated_vectors` 低但耗时差，说明上界、调度或重复选择的开销超过了节省的点积计算。与 `blocked` 比较可区分剪枝收益和连续分块遍历开销。三种模式的分数精度和 top-k 函数相同。

## 持久化与所有权

`save()` 记录格式版本、归一化原序向量、标签与建库配置。`load()` 检查格式和数组属性，验证连续非负标签，再将合法成员交给构造过程重建中心与证书。NPZ 不存储证书，因此修改持久化证书无法欺骗遍历。但 NPZ 解压仍可能占用过多内存，所以大小不可信的上传文件不在接口安全范围内。

输入数组会被复制，索引不保留查询历史。公共数组只读，元数据在访问时复制，临时数组只属于单次调用。查询不持有打开的文件或外部设备资源，因此不需要显式 close。数组由 Python 引用生命周期管理，数组字节数与进程 RSS 仍是不同指标。

## 调试与验证修改

```sh
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m mypy src/capprune
.venv/bin/python -m capprune demo --vectors 256 --dimension 12 --clusters 8 --queries 7 --k 5
```

数值不一致时，先保留种子和原始输入。对同一索引比较 `scan`、`blocked` 与 `pruned`。若仅 `pruned` 不一致，检查每个被跳过块的上界与其真实最大分数。若 `blocked` 也不一致，检查分块排列、原始 ID、top-k 并列以及稠密内核分数差异。私有数组只适合开发调试，不是受支持的外部 API。

出现性能下降时，应分别测量工作量计数与延迟，然后阅读全部原始样本，不能只选最好的一次。不要在看到结果后修改冻结目标。持久化失败时，使用归档副本复现并运行加载测试，不应仅为成功加载而绕过格式或范数验证。

默认测试离线执行真实数值代码和 CLI 子进程，不能由此推断硬件支持、远端 CI 成功、生产相关性或形式化浮点保证。已验证环境与实际实验结果见 [EXPERIMENTS.md](EXPERIMENTS.md)，实际开发修改及验证历史见 [DEVELOPMENT.md](DEVELOPMENT.md)。
