"""Offline command line interface. / 离线命令行接口。"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Never
from zipfile import BadZipFile

import numpy as np

from capprune import CapIndex


class _BilingualParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error / 错误: {message}\n")


def _positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be positive / 必须为正整数")
    return number


def _nonnegative_int(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("must be nonnegative / 必须为非负整数")
    return number


def _load_array(path: Path) -> np.ndarray[Any, Any]:
    value = np.load(path, allow_pickle=False)
    if not isinstance(value, np.ndarray):
        value.close()
        raise ValueError("expected an .npy array / 需要 .npy 数组")
    return value


def _write_json(path: Path, content: str) -> None:
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def demo(
    *,
    size: int = 4096,
    dimension: int = 32,
    clusters: int = 16,
    queries: int = 16,
    k: int = 10,
    seed: int = 7,
) -> dict[str, Any]:
    """Compare actual search paths on synthetic data. / 用合成数据比较真实搜索路径。

    This is an offline correctness demonstration, not a pretrained-model
    evaluation. / 这是离线正确性演示，不是预训练模型评测。
    """
    if min(size, dimension, clusters, queries, k) < 1 or seed < 0:
        raise ValueError("sizes must be positive; seed >= 0 / 规模必须为正，种子不得为负")
    if k > size:
        raise ValueError("k must not exceed vector count / k 不得大于向量数")
    rng = np.random.default_rng(seed)
    centers = rng.normal(size=(min(clusters, size), dimension))
    centers /= np.linalg.norm(centers, axis=1, keepdims=True)
    vectors = centers[rng.integers(len(centers), size=size)] + 0.08 * rng.normal(
        size=(size, dimension)
    )
    query_vectors = centers[rng.integers(len(centers), size=queries)] + 0.08 * rng.normal(
        size=(queries, dimension)
    )
    index = CapIndex.build(vectors, n_clusters=clusters, seed=seed)
    reference = index.search(query_vectors, k=k, mode="scan")
    result = index.search(query_vectors, k=k, mode="pruned")
    max_error = float(np.max(np.abs(reference.scores - result.scores)))
    exact_match = bool(
        np.array_equal(reference.ids, result.ids)
        and np.allclose(reference.scores, result.scores, atol=1e-12, rtol=0)
    )
    return {
        "command": "demo",
        "dataset_kind": "synthetic_clustered",
        "seed": seed,
        "size": size,
        "dimension": dimension,
        "clusters": index.n_clusters,
        "queries": queries,
        "k": k,
        "exact_match": exact_match,
        "score_tolerance": 1e-12,
        "max_absolute_score_error": max_error,
        "evaluated_fraction": float(np.sum(result.evaluated_vectors) / (size * queries)),
        "evaluated_vectors": result.evaluated_vectors.tolist(),
        "visited_blocks": result.visited_blocks.tolist(),
        "bound_evaluations": result.bound_evaluations.tolist(),
        "ids": result.ids.tolist(),
        "scores": result.scores.tolist(),
    }


def _parser() -> argparse.ArgumentParser:
    parser = _BilingualParser(
        prog="capprune",
        description="Exact cosine top-k with spherical-cap pruning / 球冠剪枝精确余弦 top-k",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    commands = parser.add_subparsers(dest="command", required=True)
    example = commands.add_parser("demo", help="run offline synthetic demo / 运行离线合成演示")
    example.add_argument(
        "--vectors", type=_positive_int, default=4096, help="vector count / 向量数"
    )
    example.add_argument("--dimension", type=_positive_int, default=32, help="dimensions / 维度")
    example.add_argument("--clusters", type=_positive_int, default=16, help="clusters / 聚类数")
    example.add_argument("--queries", type=_positive_int, default=16, help="query count / 查询数")
    example.add_argument("--k", type=_positive_int, default=10, help="result count / 结果数")
    example.add_argument("--seed", type=_nonnegative_int, default=7, help="random seed / 随机种子")
    build = commands.add_parser("build", help="build an index from .npy / 从 .npy 构建索引")
    build.add_argument("vectors", type=Path, help="2D vector .npy file / 二维向量 .npy 文件")
    build.add_argument("index", type=Path, help="output .npz index / 输出 .npz 索引")
    build.add_argument("--clusters", type=_positive_int, default=32, help="cluster count / 聚类数")
    build.add_argument(
        "--iterations", type=_positive_int, default=8, help="Lloyd rounds / Lloyd 轮数"
    )
    build.add_argument("--seed", type=_nonnegative_int, default=0, help="random seed / 随机种子")
    build.add_argument(
        "--max-matrix-mib",
        type=_positive_int,
        default=64,
        help="assignment scratch budget in MiB / 分配过程临时矩阵预算，单位 MiB",
    )
    query = commands.add_parser("query", help="search a saved index / 查询已保存索引")
    query.add_argument("index", type=Path, help="saved .npz index / 已保存的 .npz 索引")
    query.add_argument("queries", type=Path, help="1D or 2D .npy queries / 一维或二维 .npy 查询")
    query.add_argument("--k", type=_positive_int, default=10, help="result count / 结果数")
    query.add_argument(
        "--mode",
        choices=("pruned", "scan", "blocked"),
        default="pruned",
        help="search implementation / 搜索实现",
    )
    query.add_argument("--output", type=Path, help="write JSON to a file / 将 JSON 写入文件")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI; ordinary input errors return 2. / 运行 CLI；普通输入错误返回 2。"""
    parser = _parser()
    args = parser.parse_args(argv)
    output: Path | None = None
    try:
        if args.command == "demo":
            payload = demo(
                size=args.vectors,
                dimension=args.dimension,
                clusters=args.clusters,
                queries=args.queries,
                k=args.k,
                seed=args.seed,
            )
            status = 0 if payload["exact_match"] else 1
        elif args.command == "build":
            if args.vectors.resolve() == args.index.resolve():
                raise ValueError("output must differ from input / 输出路径不得与输入相同")
            index = CapIndex.build(
                _load_array(args.vectors),
                n_clusters=args.clusters,
                iterations=args.iterations,
                seed=args.seed,
                max_matrix_bytes=args.max_matrix_mib * 1024 * 1024,
            )
            index.save(args.index)
            payload = {
                "command": "build",
                "size": index.size,
                "dimension": index.dimension,
                "clusters": index.n_clusters,
                "memory_bytes": index.memory_bytes,
            }
            status = 0
        else:
            if args.output is not None and args.output.resolve() in {
                args.index.resolve(),
                args.queries.resolve(),
            }:
                raise ValueError("output must differ from inputs / 输出路径不得与输入相同")
            index = CapIndex.load(args.index)
            result = index.search(_load_array(args.queries), k=args.k, mode=args.mode)
            payload = {
                "command": "query",
                "mode": args.mode,
                "k": args.k,
                "ids": result.ids.tolist(),
                "scores": result.scores.tolist(),
                "evaluated_vectors": result.evaluated_vectors.tolist(),
                "visited_blocks": result.visited_blocks.tolist(),
                "bound_evaluations": result.bound_evaluations.tolist(),
            }
            output = args.output
            status = 0
        serialized = json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
        if output is None:
            sys.stdout.write(serialized)
        else:
            _write_json(output, serialized)
        return status
    except (OSError, ValueError, EOFError, BadZipFile) as exc:
        print(f"error / 错误: {exc}", file=sys.stderr)
        return 2
