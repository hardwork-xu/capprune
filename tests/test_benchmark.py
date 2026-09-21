"""Experiment evidence integration tests. / 实验证据集成测试。"""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

from benchmark import workload
from scripts.analyze import summarize
from scripts.evidence import source_snapshot


def test_workload_reproducible():
    case = {"n": 21, "d": 4, "clusters": 3, "noise": 0.04, "kind": "clustered"}
    a, q, source = workload(case, 91, 5)
    b, r, other = workload(case, 91, 5)
    np.testing.assert_array_equal(a, b)
    np.testing.assert_array_equal(q, r)
    assert source == other
    assert source["type"] == "synthetic"


def test_source_snapshot_avoids_private_paths():
    snapshot = source_snapshot()
    assert len(snapshot["source_sha256"]) == 64
    assert "src/capprune/index.py" in snapshot["files"]
    assert all(not name.startswith("/") for name in snapshot["files"])


def test_benchmark_evidence_roundtrip(tmp_path: Path):
    destination = tmp_path / "smoke.json"
    command = [sys.executable, "benchmark.py", "--smoke", "--output", str(destination)]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr + result.stdout
    raw = json.loads(destination.read_text())
    assert raw["status"] == "passed"
    assert raw["smoke"] is True
    assert raw["run_id"] and raw["source"]["source_sha256"]
    assert raw["environment"]["threadpools"]
    assert all(p["num_threads"] == 1 for p in raw["environment"]["threadpools"])
    samples = raw["cases"][0]["samples"]
    assert len(samples) == 24
    assert all(s["elapsed_ns"] > 0 and s["ids_equal"] and s["scores_close"] for s in samples)
    summary = summarize(raw)
    assert len(summary) == 1 and summary[0]["pruned"]["samples"] == 8
    repeated = subprocess.run(command, capture_output=True, text=True)
    assert repeated.returncode != 0
    assert json.loads(destination.read_text())["run_id"] == raw["run_id"]


def test_failure_preserves_completed_samples(monkeypatch):
    from benchmark import run_case
    from capprune import CapIndex

    protocol = json.loads(Path("configs/protocol.json").read_text())
    protocol.update(queries_per_case=2, repetitions=2, warmup_queries=0)
    case = dict(protocol["cases"][0], n=40, d=4, clusters=4, k=2)
    original = CapIndex.search
    calls = 0

    def fail_after_actual_queries(self, *args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 10:
            raise RuntimeError("injected measurement failure")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(CapIndex, "search", fail_after_actual_queries)
    progress = {}
    import pytest

    with pytest.raises(RuntimeError, match="injected"):
        run_case(case, protocol, 7, progress)
    assert 0 < len(progress["samples"]) < 12
    assert all(s["elapsed_ns"] > 0 for s in progress["samples"])
