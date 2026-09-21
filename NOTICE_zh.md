# 第三方声明与来源

[English](NOTICE.md) · [许可证](LICENSE) · [研究引用](docs/zh/RESEARCH.md)

CapPrune 的项目代码与文档采用 MIT 许可证，版权归属为 2026 CapPrune contributors。这不改变依赖、数据集、引用论文或其他第三方材料的许可证。依赖单独安装，其原始声明保留在各自发行包中。

以下元数据和许可证文件于 2026-09-21 在锁定的开发环境中核验。表格说明直接使用的软件包及数值依赖 SciPy，不能替代完整许可证文本或全部传递依赖声明。

| 软件包 | 版本 | 许可证 / 已安装发行包内的声明来源 | 用途 |
|---|---|---|---|
| NumPy | 2.2.6 | BSD-3-Clause；`numpy-2.2.6.dist-info/LICENSE.txt` 还包含捆绑库声明。 | 数组与稠密数值内核。 |
| threadpoolctl | 3.6.0 | BSD-3-Clause；`threadpoolctl-3.6.0.dist-info/licenses/LICENSE`。 | 基准实验线程控制。 |
| scikit-learn | 1.7.2 | BSD-3-Clause；`scikit_learn-1.7.2.dist-info/licenses/COPYING`，包含捆绑声明。 | 加载附带的数字数据；不提供本项目索引实现。 |
| SciPy | 1.18.1 | BSD-3-Clause；`scipy-1.18.1.dist-info/LICENSE.txt`，包含捆绑声明。 | 传递科学计算依赖。 |
| Matplotlib | 3.10.6 | 基于 PSF 许可证的 Matplotlib 许可协议；`matplotlib-3.10.6.dist-info/LICENSE`；字体另有声明。 | 实验绘图。 |
| pyparsing | 3.2.3 | MIT；`pyparsing-3.2.3.dist-info/LICENSE`。 | 固定版本的绘图解析依赖。 |
| psutil | 7.1.0 | BSD-3-Clause；`psutil-7.1.0.dist-info/LICENSE`。 | 进程内存测量。 |
| pytest | 8.4.2 | MIT；发行包内 `licenses/LICENSE`。 | 测试。 |
| Ruff | 0.13.0 | MIT；发行包内 `licenses/LICENSE`。 | 格式与静态检查。 |
| mypy | 1.18.1 | MIT；发行包内 `licenses/LICENSE`；捆绑的 typeshed 有独立声明。 | 类型检查。 |
| build | 1.3.0 | MIT；发行包内 `licenses/LICENSE`。 | 构建前端。 |
| hatchling | 1.27.0 | MIT；发行包内 `licenses/LICENSE.txt`。 | 构建后端。 |

[锁文件](uv.lock) 记录全部解析版本与分发文件哈希。重新分发依赖二进制或容器时，应保留其许可证与归属文件。本仓库源码发行包不捆绑这些依赖二进制。标准 MIT 文本保留英文，项目说明提供双语版本。

## 数据集归属

真实数据基准调用 scikit-learn 1.7.2 的 `sklearn.datasets.load_digits`。[对应版本官方文档](https://scikit-learn.org/1.7/modules/generated/sklearn.datasets.load_digits.html) 说明其包含 1,797 幅数字图像，每幅由 64 个数值特征表示，来自 UCI 数据集的测试部分。CapPrune 留出 40 行作为查询，其余 1,757 行作为数据库，再对数值特征归一化以执行余弦检索。这不是预训练嵌入数据集，也不是分类准确率实验。数据数组未复制到本仓库。

归属：**Alpaydin, E. 与 Kaynak, C.（1998）。Optical Recognition of Handwritten Digits。UCI Machine Learning Repository。[DOI: 10.24432/C50P49](https://doi.org/10.24432/C50P49)。** [UCI 数据集页面](https://archive.ics.uci.edu/dataset/80/optical+recognition+of+handwritten+digits) 标注 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。这些一手页面于 2026-09-21 核查。

所有聚类与各向同性基准场景均为生成的合成向量，种子与配置保存在结果中。仓库不包含私人数据集或模型权重。

## 算法归属与引用

角度 branch-and-bound 和球面 k-means 均为已有方法，在 [RESEARCH.md](docs/zh/RESEARCH.md) 中注明来源链接。CapPrune 不宣称这些算法为原创；此声明也不代表与引用作者或项目存在关联或获得背书。

引用本软件可使用描述性文本：**CapPrune：基于球冠分块剪枝的精确余弦检索，版本 0.1.0（2026），软件。** 同时记录实验使用的源码 revision 或产物 SHA-256。这里不指定 DOI、发表场合、公开仓库地址或个人作者信息。在必需的公开作者元数据核验前，不生成 `CITATION.cff`。
