"""Core numerical/state contracts / 核心数值与状态契约。"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pytest

from capprune import CapIndex


@pytest.mark.parametrize("dimension", [1, 2, 7, 64])
@pytest.mark.parametrize("k", [1, 7, 73])
def test_modes_match_scalar_reference(dimension: int, k: int) -> None:
    rng = np.random.default_rng(120 + dimension)
    vectors = rng.normal(size=(73, dimension))
    queries = rng.normal(size=(9, dimension))
    index = CapIndex.build(vectors, n_clusters=9, iterations=3, max_matrix_bytes=9 * 8 * 5)
    queries /= np.linalg.norm(queries, axis=1, keepdims=True)
    for mode in ("scan", "blocked", "pruned"):
        result = index.search(queries, k, mode=mode)
        for row, query in enumerate(queries):
            reference = np.array([np.dot(vector, query) for vector in index.vectors])
            order = np.lexsort((np.arange(len(vectors)), -reference))[:k]
            np.testing.assert_array_equal(result.ids[row], order)
            np.testing.assert_allclose(result.scores[row], reference[order], atol=2e-14, rtol=2e-14)
        assert np.all(result.evaluated_vectors <= len(vectors))
        if mode != "pruned":
            assert np.all(result.evaluated_vectors == len(vectors))
            assert np.all(result.bound_evaluations == 0)
        else:
            assert np.all(result.bound_evaluations == index.n_clusters)


def test_cluster_pruning_is_active() -> None:
    rng = np.random.default_rng(93)
    centers = np.eye(12)
    vectors = np.repeat(centers, 100, axis=0) + rng.normal(scale=0.01, size=(1200, 12))
    index = CapIndex.build(vectors, n_clusters=24, iterations=5)
    actual = index.search(centers, 5)
    reference = index.search(centers, 5, mode="scan")
    np.testing.assert_array_equal(actual.ids, reference.ids)
    np.testing.assert_allclose(actual.scores, reference.scores, atol=2e-14)
    assert actual.evaluated_vectors.mean() < index.size / 2
    assert np.all(actual.visited_blocks < index.n_clusters)


def test_extreme_norm_scales_and_input_ownership() -> None:
    vectors = np.array([[1e308, 1e308], [1e-308, -1e-308], [-5e-324, 5e-324]])
    original = vectors.copy()
    index = CapIndex.build(vectors, n_clusters=8)
    np.testing.assert_array_equal(vectors, original)
    np.testing.assert_allclose(np.linalg.norm(index.vectors, axis=1), 1)
    query = np.array([1e308, 1e308])
    result = index.search(query, 3)
    assert result.ids.shape == (1, 3)
    assert result.ids[0, 0] == 0
    np.testing.assert_allclose(result.scores[0], [1, 0, 0], atol=2e-15)
    vectors[:] = 1
    np.testing.assert_array_equal(index.search(query, 3).ids, result.ids)
    with pytest.raises(ValueError):
        index.vectors[0, 0] = 2
    with pytest.raises(ValueError):
        index.vectors.setflags(write=True)
    with pytest.raises(ValueError):
        result.ids[0, 0] = 99
    copy = index.metadata
    copy["build_config"]["seed"] = 99
    assert index.metadata["build_config"]["seed"] == 0


def test_ties_and_antipodal_cancellation() -> None:
    vectors = np.tile([[1.0, 0], [-1.0, 0], [0, 1.0], [0, -1.0]], (30, 1))
    index = CapIndex.build(vectors, n_clusters=1)
    for mode in ("scan", "blocked", "pruned"):
        result = index.search([[1.0, 0]], 35, mode=mode)
        np.testing.assert_array_equal(result.ids[0, :30], np.arange(0, 120, 4))
        np.testing.assert_array_equal(result.ids[0, 30:], [2, 3, 6, 7, 10])
    duplicate = CapIndex.build(np.tile([1.0, 0], (50, 1)), n_clusters=16)
    assert duplicate.n_clusters == 1
    np.testing.assert_array_equal(duplicate.search([1, 0], 7).ids[0], np.arange(7))


def test_guarded_caps_cover_members_near_endpoints() -> None:
    rng = np.random.default_rng(17)
    vectors = np.concatenate(
        (
            np.tile([1.0, 0, 0], (30, 1)) + rng.normal(scale=1e-14, size=(30, 3)),
            np.tile([-1.0, 0, 0], (30, 1)) + rng.normal(scale=1e-14, size=(30, 3)),
            rng.normal(size=(60, 3)),
        )
    )
    index = CapIndex.build(vectors, n_clusters=12)
    queries = np.concatenate((index.vectors, -index.vectors))
    for query in queries:
        bounds = index._bounds(query)
        for block in range(index.n_clusters):
            members = index.vectors[index._labels == block]
            assert np.max(members @ query) <= bounds[block]
    actual = index.search(queries, 5)
    reference = index.search(queries, 5, mode="scan")
    np.testing.assert_array_equal(actual.ids, reference.ids)
    np.testing.assert_allclose(actual.scores, reference.scores, atol=2e-14)


def test_empty_queries_singleton_and_full_k() -> None:
    index = CapIndex.build([[2.0, 0]])
    result = index.search(np.empty((0, 2)), 1)
    assert result.ids.shape == (0, 1)
    assert result.evaluated_vectors.shape == (0,)
    np.testing.assert_array_equal(index.search([2, 0], 1).ids, [[0]])
    np.testing.assert_allclose(index.search([2, 0], 1).scores, [[1]])


@pytest.mark.parametrize(
    "vectors",
    [[], [[0, 0]], [[np.nan, 1]], [[np.inf, 1]], [[1j, 2]], [["a", "b"]], [[[1]]]],
)
def test_invalid_vectors(vectors: object) -> None:
    with pytest.raises(ValueError):
        CapIndex.build(vectors)


@pytest.mark.parametrize(
    "options",
    [
        {"n_clusters": 0},
        {"n_clusters": True},
        {"iterations": 0},
        {"iterations": 1.5},
        {"seed": -1},
        {"max_matrix_bytes": 7},
        {"n_clusters": 2, "max_matrix_bytes": 8},
    ],
)
def test_invalid_build_options(options: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        CapIndex.build(np.eye(3), **options)


@pytest.mark.parametrize("queries", [[0, 0], [1, 2, 3], [np.nan, 1], [[[1, 2]]]])
def test_invalid_queries(queries: object) -> None:
    index = CapIndex.build(np.eye(2))
    with pytest.raises(ValueError):
        index.search(queries, 1)


@pytest.mark.parametrize("k", [0, -1, 3, 1.2, True])
def test_invalid_k(k: object) -> None:
    with pytest.raises(ValueError):
        CapIndex.build(np.eye(2)).search([1, 0], k)


def test_invalid_mode() -> None:
    with pytest.raises(ValueError):
        CapIndex.build(np.eye(2)).search([1, 0], 1, mode="invalid")


def test_save_load_repeat_and_concurrent_queries(tmp_path: Path) -> None:
    rng = np.random.default_rng(4)
    index = CapIndex.build(rng.normal(size=(201, 11)), n_clusters=13)
    query = rng.normal(size=(7, 11))
    expected = index.search(query, 12)
    path = tmp_path / "index.npz"
    index.save(path)
    restored = CapIndex.load(path)
    assert restored.metadata == index.metadata
    assert restored.memory_bytes == index.memory_bytes
    with ThreadPoolExecutor(max_workers=3) as executor:
        for result in executor.map(lambda _: restored.search(query, 12), range(6)):
            np.testing.assert_array_equal(result.ids, expected.ids)
            np.testing.assert_array_equal(result.scores, expected.scores)
    index.save(path)
    np.testing.assert_array_equal(CapIndex.load(path).search(query, 12).ids, expected.ids)
    with pytest.raises(OSError):
        index.save(tmp_path / "missing" / "index.npz")
    with pytest.raises(OSError):
        CapIndex.load(tmp_path / "absent.npz")


@pytest.mark.parametrize("field", ["schema", "vectors", "labels", "build_config", "extra"])
def test_tampered_archive_rejected(tmp_path: Path, field: str) -> None:
    index = CapIndex.build(np.eye(3))
    path = tmp_path / "valid.npz"
    index.save(path)
    with np.load(path, allow_pickle=False) as archive:
        payload = {name: archive[name] for name in archive.files}
    replacements = {
        "schema": np.array(999),
        "vectors": np.zeros((3, 3)),
        "labels": np.array([0, 2, 2], dtype=np.int64),
        "build_config": np.array("{}"),
        "extra": np.array("unexpected"),
    }
    payload[field] = replacements[field]
    np.savez(path, **payload)
    with pytest.raises(ValueError):
        CapIndex.load(path)


def test_failed_atomic_replace_preserves_saved_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import capprune.index as core

    path = tmp_path / "index.npz"
    CapIndex.build(np.eye(3)).save(path)
    before = path.read_bytes()

    def fail_replace(source: object, destination: object) -> None:
        # Serialization has completed; inject the filesystem's final-commit failure.
        # 序列化已经真实完成，在文件系统最终替换步骤注入故障。
        raise OSError("injected replace failure")

    monkeypatch.setattr(core.os, "replace", fail_replace)
    with pytest.raises(OSError, match="injected replace failure"):
        CapIndex.build(np.eye(4)).save(path)
    assert path.read_bytes() == before
    assert not list(tmp_path.glob(".capprune-*.tmp"))
    assert CapIndex.load(path).size == 3


def test_truncated_zip_rejected(tmp_path: Path) -> None:
    path = tmp_path / "index.npz"
    CapIndex.build(np.eye(3)).save(path)
    path.write_bytes(path.read_bytes()[:-22])
    with pytest.raises(ValueError, match="invalid index archive"):
        CapIndex.load(path)
