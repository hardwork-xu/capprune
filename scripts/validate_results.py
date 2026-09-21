"""Validate raw evidence and relevant source fingerprints. / 验证原始证据与相关源码指纹。"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate(path: Path) -> dict:
    raw = json.loads(path.read_text())
    assert raw["schema_version"] == 1
    assert raw["status"] == "passed", "Recorded failures / 存在失败记录"
    assert raw["run_id"] and raw["started_at"] and raw["finished_at"]
    protocol = raw["protocol"]
    assert len(raw["cases"]) == len(protocol["cases"])
    assert all(v == "1" for v in raw["environment"]["requested_thread_environment"].values())
    count = 0
    for case in raw["cases"]:
        assert case["status"] == "passed" and case["correctness"]["all_passed"]
        expected = protocol["queries_per_case"] * protocol["repetitions"] * len(protocol["modes"])
        assert len(case["samples"]) == expected
        keys = {(s["repeat"], s["query_id"], s["mode"]) for s in case["samples"]}
        assert keys == {
            (r, q, m)
            for r in range(protocol["repetitions"])
            for q in range(protocol["queries_per_case"])
            for m in protocol["modes"]
        }
        for sample in case["samples"]:
            assert sample["elapsed_ns"] > 0
            assert sample["ids_equal"] and sample["scores_close"]
            assert 0 < sample["evaluated_vectors"] <= case["actual_shape"][0]
        count += expected
    for name, digest in raw["source"]["files"].items():
        if name.startswith("src/") or name in {
            "benchmark.py",
            "scripts/evidence.py",
            "configs/protocol.json",
            "uv.lock",
            "pyproject.toml",
        }:
            assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    return {"cases": len(raw["cases"]), "samples": count, "run_id": raw["run_id"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(args.path)))


if __name__ == "__main__":
    main()
