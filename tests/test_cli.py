"""Real process-level CLI coverage. / 真实进程级 CLI 覆盖。"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from capprune import CapIndex


def invoke(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "capprune", *arguments],
        capture_output=True,
        text=True,
        check=False,
    )


def test_demo_is_real_and_repeatable() -> None:
    args = (
        "demo",
        "--vectors",
        "256",
        "--dimension",
        "12",
        "--clusters",
        "8",
        "--queries",
        "7",
        "--k",
        "5",
    )
    first = invoke(*args)
    second = invoke(*args)
    assert first.returncode == second.returncode == 0, first.stderr
    assert first.stdout == second.stdout
    result = json.loads(first.stdout)
    assert result["dataset_kind"] == "synthetic_clustered"
    assert result["exact_match"]
    assert 0 < result["evaluated_fraction"] <= 1
    assert len(result["ids"]) == 7
    assert len(result["ids"][0]) == 5
    assert result["max_absolute_score_error"] <= result["score_tolerance"]


@pytest.mark.parametrize("mode", ["pruned", "scan", "blocked"])
def test_build_query_roundtrip(tmp_path: Path, mode: str) -> None:
    rng = np.random.default_rng(19)
    vectors = rng.normal(size=(63, 9))
    queries = rng.normal(size=(4, 9))
    vector_path, query_path = tmp_path / "vectors.npy", tmp_path / "queries.npy"
    index_path, output_path = tmp_path / "index.npz", tmp_path / "results.json"
    np.save(vector_path, vectors)
    np.save(query_path, queries)
    built = invoke("build", str(vector_path), str(index_path), "--clusters", "7")
    assert built.returncode == 0, built.stderr
    assert json.loads(built.stdout)["size"] == len(vectors)
    searched = invoke(
        "query",
        str(index_path),
        str(query_path),
        "--k",
        "6",
        "--mode",
        mode,
        "--output",
        str(output_path),
    )
    assert searched.returncode == 0, searched.stderr
    assert searched.stdout == ""
    result = json.loads(output_path.read_text())
    expected = CapIndex.load(index_path).search(queries, k=6, mode="scan")
    np.testing.assert_array_equal(result["ids"], expected.ids)
    np.testing.assert_allclose(result["scores"], expected.scores, rtol=0, atol=1e-12)


def test_query_accepts_single_vector(tmp_path: Path) -> None:
    index_path, query_path = tmp_path / "index.npz", tmp_path / "query.npy"
    CapIndex.build(np.eye(3), n_clusters=3).save(index_path)
    np.save(query_path, np.array([1.0, 0.0, 0.0]))
    result = invoke("query", str(index_path), str(query_path), "--k", "1")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["ids"] == [[0]]


@pytest.mark.parametrize(
    "arguments",
    [
        ("demo", "--vectors", "0"),
        ("demo", "--seed", "-1"),
        ("demo", "--vectors", "2", "--k", "3"),
        ("query", "missing.npz", "missing.npy"),
    ],
)
def test_errors_are_nonzero_without_tracebacks(arguments: tuple[str, ...]) -> None:
    result = invoke(*arguments)
    assert result.returncode == 2
    assert "Traceback" not in result.stderr
    assert result.stderr


def test_rejects_archive_instead_of_array(tmp_path: Path) -> None:
    path = tmp_path / "vectors.npz"
    np.savez(path, vectors=np.eye(3))
    result = invoke("build", str(path), str(tmp_path / "index.npz"))
    assert result.returncode == 2
    assert "需要 .npy 数组" in result.stderr


def test_rejects_nonfinite_vectors(tmp_path: Path) -> None:
    path = tmp_path / "vectors.npy"
    np.save(path, np.array([[float("nan"), 1.0]]))
    result = invoke("build", str(path), str(tmp_path / "index.npz"))
    assert result.returncode == 2
    assert "Traceback" not in result.stderr


def test_inputs_cannot_be_overwritten(tmp_path: Path) -> None:
    vector_path, index_path = tmp_path / "vectors.npy", tmp_path / "index.npz"
    np.save(vector_path, np.eye(3))
    original = vector_path.read_bytes()
    build = invoke("build", str(vector_path), str(vector_path))
    assert build.returncode == 2
    assert vector_path.read_bytes() == original
    CapIndex.build(np.eye(3), n_clusters=3).save(index_path)
    query = invoke(
        "query", str(index_path), str(vector_path), "--k", "1", "--output", str(vector_path)
    )
    assert query.returncode == 2
    assert vector_path.read_bytes() == original


def test_output_write_failure_is_reported(tmp_path: Path) -> None:
    vector_path, index_path = tmp_path / "vectors.npy", tmp_path / "index.npz"
    np.save(vector_path, np.eye(3))
    CapIndex.build(np.eye(3), n_clusters=3).save(index_path)
    result = invoke(
        "query",
        str(index_path),
        str(vector_path),
        "--k",
        "1",
        "--output",
        str(tmp_path / "absent" / "result.json"),
    )
    assert result.returncode == 2
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("command", [(), ("demo",), ("build",), ("query",)])
def test_help_is_bilingual(command: tuple[str, ...]) -> None:
    result = invoke(*command, "--help")
    assert result.returncode == 0
    assert any("\u4e00" <= character <= "\u9fff" for character in result.stdout)
    assert "usage:" in result.stdout
