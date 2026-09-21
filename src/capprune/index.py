"""Exact-arithmetic spherical-cap search with guarded float64 bounds.

球面帽上界搜索：精确算术下精确，float64 路径采用保守数值余量。
"""

from __future__ import annotations

import json
import os
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
Mode = Literal["pruned", "scan", "blocked"]
_SCHEMA = 1
_VERSION = "0.1.0"


def _integer(value: Any, name: str, minimum: int = 1) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise ValueError(f"{name} must be an integer / {name} 必须为整数")
    result = int(value)
    if result < minimum:
        raise ValueError(f"{name} must be >= {minimum} / {name} 必须 >= {minimum}")
    return result


def _normalize(values: ArrayLike, *, name: str, dimension: int | None = None) -> FloatArray:
    raw = np.asarray(values)
    if raw.dtype.kind not in "fiu":
        raise ValueError(f"{name} must contain real numbers / {name} 必须包含实数")
    array = np.array(raw, dtype=np.float64, order="C", copy=True)
    if dimension is not None and array.ndim == 1:
        array = array.reshape(1, -1)
    if array.ndim != 2 or array.shape[1] == 0:
        raise ValueError(f"{name} must have shape (rows, dimensions) / {name} 必须为二维矩阵")
    if dimension is not None and array.shape[1] != dimension:
        raise ValueError(f"{name} dimension mismatch / {name} 维度不匹配")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} must be finite / {name} 不得包含 NaN 或 Inf")
    if not len(array):
        if dimension is None:
            raise ValueError("vectors cannot be empty / 向量库不能为空")
        return array
    # Scale first: neither huge finite inputs nor subnormal values overflow norms.
    # 先缩放再求范数，避免有限大数溢出或极小数下溢。
    scale = np.max(np.abs(array), axis=1)
    if np.any(scale == 0):
        raise ValueError(f"{name} contains zero vectors / {name} 包含零向量")
    array /= scale[:, None]
    array /= np.sqrt(np.einsum("ij,ij->i", array, array))[:, None]
    return array


def _readonly(array: NDArray[Any]) -> NDArray[Any]:
    array.setflags(write=False)
    return array


def _topk(scores: FloatArray, ids: IntArray, k: int) -> tuple[FloatArray, IntArray]:
    """Partial selection retaining every cutoff tie / 保留分界处全部并列项。"""
    if len(scores) > k:
        boundary = np.partition(scores, len(scores) - k)[len(scores) - k]
        candidates = np.flatnonzero(scores >= boundary)
        scores, ids = scores[candidates], ids[candidates]
    order = np.lexsort((ids, -scores))[:k]
    return scores[order], ids[order]


@dataclass(frozen=True)
class SearchResult:
    """Immutable results; rows are queries, IDs refer to original vector order.

    不可变搜索结果；行对应查询，ID 对应建库时的原始向量顺序。
    Counters are per query; bounds count is zero for scan and blocked modes.
    计数器按查询记录；scan 与 blocked 模式的上界计算数为零。
    """

    ids: IntArray
    scores: FloatArray
    evaluated_vectors: IntArray
    visited_blocks: IntArray
    bound_evaluations: IntArray


class CapIndex:
    """An immutable CPU cosine index with deterministic score/ID tie breaking.

    不可变 CPU 余弦索引，以分数降序、原始 ID 升序处理并列。
    Use ``build`` or ``load``; searches have no shared mutable scratch state.
    使用 build 或 load 创建；查询之间没有共享的可变临时状态。
    """

    def __init__(self, vectors: FloatArray, labels: IntArray, config: dict[str, int]) -> None:
        # Construction receives owned normalized vectors; all published arrays are read-only.
        # 内部构造接收独立的归一化数组；公开数组均设为只读。
        self._vectors = vectors
        self._labels = labels
        self._config = dict(config)
        self._margin = 64.0 * np.finfo(np.float64).eps * max(1, vectors.shape[1])
        self._order = np.argsort(labels, kind="stable").astype(np.int64)
        counts = np.bincount(labels)
        self._offsets = np.concatenate(([0], np.cumsum(counts))).astype(np.int64)
        self._blocked = np.ascontiguousarray(vectors[self._order])
        self._centers = np.empty((len(counts), vectors.shape[1]), dtype=np.float64)
        self._cap_min = np.empty(len(counts), dtype=np.float64)
        for block in range(len(counts)):
            members = self._blocked[self._offsets[block] : self._offsets[block + 1]]
            mean = members.mean(axis=0)
            if not np.any(mean):
                mean = members[0].copy()
            center = _normalize(mean.reshape(1, -1), name="centroid")[0]
            self._centers[block] = center
            # Lower the cap cosine before taking square roots, not just the final bound.
            # 在平方根之前降低帽边界余弦，使舍入误差只会扩大覆盖范围。
            self._cap_min[block] = np.clip(np.min(members @ center) - self._margin, -1, 1)
        for array in (
            self._vectors,
            self._labels,
            self._order,
            self._offsets,
            self._blocked,
            self._centers,
            self._cap_min,
        ):
            _readonly(array)

    @classmethod
    def build(
        cls,
        vectors: ArrayLike,
        *,
        n_clusters: int = 32,
        iterations: int = 8,
        seed: int = 0,
        max_matrix_bytes: int = 64 * 1024 * 1024,
    ) -> CapIndex:
        """Build deterministic spherical k-means blocks from finite nonzero rows.

        从有限非零行向量构建确定性的球面 k-means 分块。
        ``n_clusters`` is clamped to N; empty clusters are dropped. The byte cap
        limits assignment score matrices, not total index or BLAS workspace.
        簇数截断为 N，移除空簇；字节上限仅约束分配分数矩阵，不是总内存。
        Invalid shapes, nonfinite/zero rows or invalid options raise ValueError.
        非法形状、非有限/零向量或非法配置抛出 ValueError。
        """
        count = _integer(n_clusters, "n_clusters")
        rounds = _integer(iterations, "iterations")
        random_seed = _integer(seed, "seed", 0)
        budget = _integer(max_matrix_bytes, "max_matrix_bytes", 8)
        normalized = _normalize(vectors, name="vectors")
        count = min(count, len(normalized))
        if budget < count * 8:
            raise ValueError(
                "byte budget cannot hold one assignment row / 内存预算不足一行分配矩阵"
            )
        rows = max(1, budget // (8 * count))
        rng = np.random.default_rng(random_seed)
        centers = normalized[rng.choice(len(normalized), count, replace=False)].copy()
        labels = np.zeros(len(normalized), dtype=np.int64)
        for _ in range(rounds):
            for start in range(0, len(normalized), rows):
                stop = min(start + rows, len(normalized))
                labels[start:stop] = np.argmax(normalized[start:stop] @ centers.T, axis=1)
            new_centers = np.zeros_like(centers)
            np.add.at(new_centers, labels, normalized)
            scale = np.max(np.abs(new_centers), axis=1)
            nonzero = scale > 0
            if np.any(nonzero):
                new_centers[nonzero] = _normalize(new_centers[nonzero], name="centroids")
            # Keeping the old center lets empty or antipodally cancelled clusters recover.
            # 空簇或正反向抵消时保留旧中心，下轮仍有机会获得成员。
            new_centers[~nonzero] = centers[~nonzero]
            centers = new_centers
        # Labels define the partition; certificates are recomputed from every member.
        # 标签定义最终分块；证书从每一个实际成员重新计算。
        _, compact = np.unique(labels, return_inverse=True)
        config = {
            "n_clusters": _integer(n_clusters, "n_clusters"),
            "iterations": rounds,
            "seed": random_seed,
            "max_matrix_bytes": budget,
        }
        return cls(normalized, compact.astype(np.int64), config)

    @property
    def size(self) -> int:
        """Number of indexed vectors / 库内向量数。"""
        return int(len(self._vectors))

    @property
    def dimension(self) -> int:
        """Vector dimension / 向量维数。"""
        return int(self._vectors.shape[1])

    @property
    def n_clusters(self) -> int:
        """Number of nonempty blocks / 非空分块数。"""
        return int(len(self._cap_min))

    @property
    def vectors(self) -> FloatArray:
        """Read-only normalized vectors in original order / 原序归一化只读向量。"""
        return self._vectors.view()

    @property
    def memory_bytes(self) -> int:
        """Owned ndarray bytes, excluding Python/BLAS overhead; not RSS.

        自有 ndarray 字节数，不含 Python/BLAS 开销；并非进程 RSS。
        """
        return sum(
            a.nbytes
            for a in (
                self._vectors,
                self._labels,
                self._order,
                self._offsets,
                self._blocked,
                self._centers,
                self._cap_min,
            )
        )

    @property
    def metadata(self) -> dict[str, Any]:
        """Independent metadata mapping / 独立元数据字典。"""
        return {
            "schema": _SCHEMA,
            "version": _VERSION,
            "size": self.size,
            "dimension": self.dimension,
            "n_clusters": self.n_clusters,
            "dtype": "float64",
            "numerical_margin": self._margin,
            "build_config": dict(self._config),
        }

    def _bounds(self, query: FloatArray) -> FloatArray:
        # On a < s the angular upper bound increases in a and decreases in s.
        # a < s 区间内，上界随 a 增加而增加，随 s 降低而增加。
        a = np.clip(self._centers @ query + self._margin, -1.0, 1.0)
        s = self._cap_min
        bounds = np.ones(self.n_clusters, dtype=np.float64)
        outside = a < s
        aa, ss = a[outside], s[outside]
        bounds[outside] = aa * ss + np.sqrt((1 - aa) * (1 + aa)) * np.sqrt((1 - ss) * (1 + ss))
        return np.nextafter(bounds + self._margin, np.inf)

    def search(self, queries: ArrayLike, k: int = 10, *, mode: Mode = "pruned") -> SearchResult:
        """Return cosine top-k for one row or a matrix, always shaped (nq, k).

        返回单向量或查询矩阵的余弦 top-k；结果始终为 (nq, k)。
        Modes: scan is one full BLAS matvec per query; blocked visits all blocks;
        pruned skips only blocks whose guarded bound is strictly below cutoff.
        scan 每条查询执行全库矩阵向量乘；blocked 遍历全块；pruned 保守剪枝。
        ``1 <= k <= size``; empty batches are valid. Queries are normalized and
        must be finite, nonzero and dimension-compatible. No input is mutated.
        k 必须位于 [1,size]；允许空查询批次；查询须有限非零且维度匹配，不修改输入。
        """
        limit = _integer(k, "k")
        if limit > self.size:
            raise ValueError("k cannot exceed index size / k 不得超过向量数")
        if mode not in ("pruned", "scan", "blocked"):
            raise ValueError(
                "mode must be pruned, scan or blocked / 模式必须为 pruned、scan 或 blocked"
            )
        normalized = _normalize(queries, name="queries", dimension=self.dimension)
        ids = np.empty((len(normalized), limit), dtype=np.int64)
        scores = np.empty((len(normalized), limit), dtype=np.float64)
        evaluated = np.zeros(len(normalized), dtype=np.int64)
        visited = np.zeros(len(normalized), dtype=np.int64)
        bound_counts = np.zeros(len(normalized), dtype=np.int64)
        original_ids = (
            np.arange(self.size, dtype=np.int64) if mode == "scan" else np.empty(0, dtype=np.int64)
        )
        for row, query in enumerate(normalized):
            if mode == "scan":
                scores[row], ids[row] = _topk(self._vectors @ query, original_ids, limit)
                evaluated[row] = self.size
                visited[row] = self.n_clusters
                continue
            if mode == "pruned":
                upper = self._bounds(query)
                order = np.argsort(-upper, kind="stable")
                bound_counts[row] = self.n_clusters
            else:
                upper = np.full(self.n_clusters, np.inf)
                order = np.arange(self.n_clusters)
            best_scores: FloatArray = np.empty(0, dtype=np.float64)
            best_ids: IntArray = np.empty(0, dtype=np.int64)
            for block in order:
                # Equality must be visited: another block may contain a smaller ID.
                # 相等上界不可剪枝：另一分块可能包含 ID 更小的并列候选。
                if len(best_scores) == limit and upper[block] < best_scores[-1]:
                    break
                start, stop = self._offsets[block : block + 2]
                block_scores = self._blocked[start:stop] @ query
                best_scores, best_ids = _topk(
                    np.concatenate((best_scores, block_scores)),
                    np.concatenate((best_ids, self._order[start:stop])),
                    limit,
                )
                evaluated[row] += stop - start
                visited[row] += 1
            scores[row], ids[row] = best_scores, best_ids
        for array in (ids, scores, evaluated, visited, bound_counts):
            _readonly(array)
        return SearchResult(ids, scores, evaluated, visited, bound_counts)

    def save(self, path: str | Path) -> None:
        """Atomically replace a non-pickle NPZ index; filesystem failures propagate.

        原子替换不含 pickle 的 NPZ 索引；文件系统异常直接传播。
        Centroids/caps are not persisted: load recomputes them from members.
        不保存中心和球面帽：加载时从成员重新计算，避免信任外部证书。
        """
        target = Path(path)
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=target.parent, prefix=".capprune-", suffix=".tmp", delete=False
            ) as handle:
                temporary = Path(handle.name)
                np.savez_compressed(
                    handle,
                    schema=np.array(_SCHEMA, dtype=np.int64),
                    vectors=self._vectors,
                    labels=self._labels,
                    build_config=np.array(json.dumps(self._config, sort_keys=True)),
                )
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    @classmethod
    def load(cls, path: str | Path) -> CapIndex:
        """Load a validated NPZ index and rebuild all pruning certificates.

        加载并验证 NPZ 索引，重建全部剪枝证书。
        Malformed archives raise ValueError; missing files raise OSError.
        格式不正确抛出 ValueError；文件系统错误抛出 OSError。
        Only local trusted-size archives should be loaded (no decompression quota).
        仅加载大小可信的本地文件；此接口不提供解压内存配额。
        """
        try:
            with np.load(path, allow_pickle=False) as archive:
                if set(archive.files) != {"schema", "vectors", "labels", "build_config"}:
                    raise ValueError("invalid index fields / 索引字段不正确")
                schema = archive["schema"]
                if schema.shape != () or schema.dtype.kind not in "iu" or int(schema) != _SCHEMA:
                    raise ValueError("unsupported index schema / 不支持的索引格式版本")
                vectors = np.array(archive["vectors"], copy=True, order="C")
                labels = np.array(archive["labels"], copy=True)
                raw_config = archive["build_config"]
                if raw_config.shape != () or raw_config.dtype.kind != "U":
                    raise ValueError("invalid build configuration / 建库配置不正确")
                config = json.loads(str(raw_config))
        except (KeyError, TypeError, EOFError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
            raise ValueError("invalid index archive / 索引文件不正确") from exc
        if vectors.dtype != np.float64 or vectors.ndim != 2 or 0 in vectors.shape:
            raise ValueError("invalid stored vectors / 保存的向量不正确")
        if not np.isfinite(vectors).all():
            raise ValueError("nonfinite stored vectors / 保存的向量包含非有限值")
        norms = np.einsum("ij,ij->i", vectors, vectors)
        tolerance = 64.0 * np.finfo(np.float64).eps * vectors.shape[1]
        if not np.all(np.abs(norms - 1.0) <= tolerance):
            raise ValueError("stored vectors must be normalized / 保存的向量必须归一化")
        if labels.dtype != np.int64 or labels.shape != (len(vectors),):
            raise ValueError("invalid stored labels / 保存的标签不正确")
        unique = np.unique(labels)
        if not np.array_equal(unique, np.arange(len(unique))):
            raise ValueError("labels must be contiguous and nonnegative / 标签须为连续非负整数")
        expected = {"n_clusters", "iterations", "seed", "max_matrix_bytes"}
        if not isinstance(config, dict) or set(config) != expected:
            raise ValueError("invalid build configuration / 建库配置不正确")
        validated = {
            key: _integer(value, key, 0 if key == "seed" else 1) for key, value in config.items()
        }
        return cls(vectors, labels, validated)
