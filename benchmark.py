#!/usr/bin/env python3
"""Reproducible single-query CPU benchmark. / 可复现的单查询 CPU 基准。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import sys
import tempfile
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

for _thread_variable in ("VECLIB_MAXIMUM_THREADS", "OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ[_thread_variable] = "1"

import numpy as np  # noqa: E402
import psutil  # noqa: E402
from sklearn.datasets import load_digits  # noqa: E402
from threadpoolctl import threadpool_limits  # noqa: E402

from capprune import CapIndex  # noqa: E402
from scripts.evidence import environment, source_snapshot  # noqa: E402


def workload(case: dict[str, Any], seed: int, nq: int) -> tuple[np.ndarray, np.ndarray, dict]:
    rng = np.random.default_rng(seed)
    n, d = case["n"], case["d"]
    if case["kind"] == "digits":
        digits = np.asarray(load_digits().data, dtype=np.float64)
        permutation = rng.permutation(len(digits))
        queries = digits[permutation[:nq]]
        vectors = digits[permutation[nq : nq + n]]
        source = {
            "type": "real",
            "name": "sklearn.datasets.load_digits",
            "version": "scikit-learn 1.7.2",
            "features": "raw 8x8 pixel intensities",
            "split": "seeded permutation, held-out queries, no training or model",
        }
    elif case["kind"] == "clustered":
        centers = rng.normal(size=(case["clusters"], d))
        centers /= np.linalg.norm(centers, axis=1, keepdims=True)
        vectors = centers[rng.integers(len(centers), size=n)]
        vectors = vectors + rng.normal(scale=case["noise"], size=(n, d))
        queries = centers[rng.integers(len(centers), size=nq)]
        queries = queries + rng.normal(scale=case["noise"], size=(nq, d))
        source = {"type": "synthetic", "distribution": "unit centers plus Gaussian noise"}
    else:
        vectors, queries = rng.normal(size=(n, d)), rng.normal(size=(nq, d))
        source = {"type": "synthetic", "distribution": "isotropic Gaussian"}
    source["sha256"] = hashlib.sha256(vectors.tobytes() + queries.tobytes()).hexdigest()
    return vectors, queries, source


def peak_rss() -> int:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == "darwin" else value * 1024)


def run_case(case: dict, protocol: dict, seed: int, progress: dict | None = None) -> dict:
    vectors, queries, data_source = workload(case, seed, protocol["queries_per_case"])
    result: dict[str, Any] = {} if progress is None else progress
    result.update(
        {
            "name": case["name"],
            "config": case,
            "seed": seed,
            "data_source": data_source,
            "samples": [],
            "status": "running",
            "actual_shape": list(vectors.shape),
            "process_peak_rss_before_bytes": peak_rss(),
        }
    )
    start = time.perf_counter_ns()
    index = CapIndex.build(
        vectors,
        n_clusters=case["clusters"],
        seed=seed,
        iterations=protocol["cluster_iterations"],
        max_matrix_bytes=protocol["assignment_budget_bytes"],
    )
    result["build_ns"] = time.perf_counter_ns() - start
    result["index_array_bytes"] = index.memory_bytes
    result["actual_clusters"] = index.n_clusters
    process = psutil.Process()
    result["process_rss_after_build_bytes"] = process.memory_info().rss
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "index.npz"
        start = time.perf_counter_ns()
        index.save(path)
        result["save_ns"] = time.perf_counter_ns() - start
        result["serialized_bytes"] = path.stat().st_size
        start = time.perf_counter_ns()
        loaded = CapIndex.load(path)
        result["load_ns"] = time.perf_counter_ns() - start
        result["roundtrip_ids_equal"] = bool(
            np.array_equal(
                loaded.search(queries[:1], case["k"]).ids, index.search(queries[:1], case["k"]).ids
            )
        )
        del loaded
    # Same full-scan oracle, computed outside timers. / 扫描参考结果不计入计时。
    reference = index.search(queries, case["k"], mode="scan")
    result["first_query_ns"] = {}
    for mode in protocol["modes"]:
        start = time.perf_counter_ns()
        index.search(queries[0], case["k"], mode=mode)
        result["first_query_ns"][mode] = time.perf_counter_ns() - start
        for q in queries[: protocol["warmup_queries"]]:
            index.search(q, case["k"], mode=mode)
    rng = np.random.default_rng(seed + 1)
    all_correct = True
    max_error = 0.0
    for repeat in range(protocol["repetitions"]):
        for qi in rng.permutation(len(queries)):
            for mode in rng.permutation(protocol["modes"]):
                start = time.perf_counter_ns()
                actual = index.search(queries[qi], case["k"], mode=str(mode))
                elapsed = time.perf_counter_ns() - start
                equal = bool(np.array_equal(actual.ids[0], reference.ids[qi]))
                error = float(np.max(np.abs(actual.scores[0] - reference.scores[qi])))
                close = bool(
                    np.allclose(
                        actual.scores[0],
                        reference.scores[qi],
                        atol=protocol["correctness"]["score_atol"],
                        rtol=protocol["correctness"]["score_rtol"],
                    )
                )
                all_correct &= equal and close
                max_error = max(max_error, error)
                result["samples"].append(
                    {
                        "repeat": repeat,
                        "query_id": int(qi),
                        "mode": str(mode),
                        "elapsed_ns": elapsed,
                        "ids_equal": equal,
                        "scores_close": close,
                        "max_abs_error": error,
                        "evaluated_vectors": int(actual.evaluated_vectors[0]),
                        "visited_blocks": int(actual.visited_blocks[0]),
                        "bound_evaluations": int(actual.bound_evaluations[0]),
                    }
                )
    result["correctness"] = {"all_passed": all_correct, "max_abs_error": max_error}
    result["process_peak_rss_after_bytes"] = peak_rss()
    result["status"] = "passed" if all_correct and result["roundtrip_ids_equal"] else "failed"
    return result


def atomic_json(path: Path, record: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_text(json.dumps(record, indent=2) + "\n")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/protocol.json"),
        help="Frozen configuration / 冻结配置",
    )
    parser.add_argument("--output", type=Path, required=True, help="New JSON file / 新建结果文件")
    parser.add_argument(
        "--smoke", action="store_true", help="Small validation, not primary / 小规模检查"
    )
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; choose a new path / 结果已存在，请选择新路径")
    protocol = json.loads(args.config.read_text())
    if protocol["threads"] != 1:
        parser.error("This runner requires threads=1 / 此脚本要求线程预算为 1")
    if args.smoke:
        protocol["repetitions"] = 2
        protocol["queries_per_case"] = 4
        protocol["cases"] = [dict(protocol["cases"][0], n=200, clusters=8)]
    record: dict[str, Any] = {
        "schema_version": 1,
        "run_id": str(uuid.uuid4()),
        "started_at": datetime.now(UTC).isoformat(),
        "command": "python benchmark.py "
        + " ".join(str(Path(v).name) if v.startswith("/") else v for v in sys.argv[1:]),
        "protocol": protocol,
        "smoke": args.smoke,
        "source": source_snapshot(),
        "cases": [],
        "memory_note": (
            "RSS includes interpreter, inputs, build, IO and prior cases; "
            "peak is cumulative process high-water mark, not per-method memory. "
            "index_array_bytes counts retained NumPy payload only."
        ),
        "timing_note": (
            "Steady-state online batch=1 search API; not application end-to-end. "
            "first_query_ns is first timed call after correctness/IO preparation, "
            "not cold startup."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with threadpool_limits(limits=protocol["threads"]):
        record["environment"] = environment()
        for i, case in enumerate(protocol["cases"]):
            result: dict[str, Any] = {"name": case["name"], "config": case, "samples": []}
            try:
                run_case(case, protocol, protocol["seed"] + i, result)
            except Exception as error:  # Preserve valid samples and report the failure.
                result.update(
                    {
                        "name": case["name"],
                        "config": case,
                        "status": "failed",
                        "error_type": type(error).__name__,
                        "error": str(error).replace(str(Path.home()), "<HOME>"),
                    }
                )
            record["cases"].append(result)
            record["finished_at"] = datetime.now(UTC).isoformat()
            record["status"] = (
                "passed" if all(c["status"] == "passed" for c in record["cases"]) else "failed"
            )
            atomic_json(args.output, record)
            print(f"{case['name']}: {result['status']}", flush=True)
    return 0 if record["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
