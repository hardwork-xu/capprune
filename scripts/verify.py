"""Run acceptance and preserve sanitized logs. / 执行验收并保存脱敏日志。"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.evidence import source_snapshot  # noqa: E402


def main() -> int:
    output = ROOT / "results/acceptance"
    output.mkdir(parents=True, exist_ok=True)
    uv = shutil.which("uv") or os.environ.get("CAPPRUNE_UV")
    commands = [
        ("format", [".venv/bin/ruff", "format", "--check", "."]),
        ("lint", [".venv/bin/ruff", "check", "."]),
        ("types", [".venv/bin/mypy"]),
        (
            "unit_tests",
            [
                ".venv/bin/python",
                "-m",
                "pytest",
                "tests/test_core.py",
                "--junitxml=results/acceptance/unit.xml",
            ],
        ),
        (
            "integration_tests",
            [
                ".venv/bin/python",
                "-m",
                "pytest",
                "tests/test_cli.py",
                "tests/test_benchmark.py",
                "--junitxml=results/acceptance/integration.xml",
            ],
        ),
        ("default_example", [".venv/bin/python", "-m", "capprune", "demo"]),
        ("example_script", [".venv/bin/python", "examples/demo.py"]),
        (
            "public_api",
            [
                ".venv/bin/python",
                "-c",
                "import numpy as np; from capprune import CapIndex; "
                "i=CapIndex.build(np.eye(3), n_clusters=3); "
                "assert i.search([1.,0.,0.], k=1).ids.tolist()==[[0]]; print('API passed')",
            ],
        ),
        (
            "benchmark_evidence",
            [".venv/bin/python", "scripts/validate_results.py", "results/reference.json"],
        ),
        ("analysis", [".venv/bin/python", "scripts/analyze.py", "results/reference.json"]),
        ("build", [".venv/bin/python", "-m", "build", "--no-isolation"]),
        ("docs", [".venv/bin/python", "scripts/check_docs.py"]),
        ("git_diff", ["git", "diff", "--check"]),
        ("public_file_audit", [".venv/bin/python", "scripts/audit.py"]),
    ]
    if uv:
        commands += [
            ("clean_install", [uv, "sync", "--frozen", "--offline", "--no-dev"]),
            (
                "wheel_install",
                [
                    uv,
                    "pip",
                    "install",
                    "--python",
                    ".verify-venv/bin/python",
                    "--no-deps",
                    "--reinstall",
                    "dist/capprune-0.1.0-py3-none-any.whl",
                ],
            ),
            ("clean_demo", [".verify-venv/bin/python", "-m", "capprune", "demo"]),
        ]
    records = []
    snapshot = source_snapshot()
    (output / "checks.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "recorded_at": datetime.now(UTC).isoformat(),
                "source": snapshot,
                "checks": [],
                "status": "running",
            },
            indent=2,
        )
        + "\n"
    )
    for name, command in commands:
        env = dict(
            os.environ,
            MPLBACKEND="Agg",
            VECLIB_MAXIMUM_THREADS="1",
            OPENBLAS_NUM_THREADS="1",
            OMP_NUM_THREADS="1",
        )
        if name == "clean_install":
            if (ROOT / ".verify-venv").exists():
                shutil.rmtree(ROOT / ".verify-venv")
            env["UV_PROJECT_ENVIRONMENT"] = ".verify-venv"
        start = time.perf_counter()
        completed = subprocess.run(
            command, cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        for xml_path in output.glob("*.xml"):
            tree = ET.parse(xml_path)
            for node in tree.iter():
                if "hostname" in node.attrib:
                    node.attrib["hostname"] = "local"
            tree.write(xml_path, encoding="unicode")
        clean = completed.stdout.replace(str(ROOT), "<PROJECT>")
        clean = clean.replace(str(Path.home()), "<HOME>")
        clean = re.sub(r"/Library/Frameworks/[^\s]+", "<PYTHON_RUNTIME>", clean)
        (output / f"{name}.log").write_text(clean)
        public_command = ["uv" if uv and item == uv else item for item in command]
        record = {
            "name": name,
            "command": public_command,
            "status": "passed" if completed.returncode == 0 else "failed",
            "exit_code": completed.returncode,
            "environment_overrides": {
                key: env[key]
                for key in [
                    "VECLIB_MAXIMUM_THREADS",
                    "OPENBLAS_NUM_THREADS",
                    "OMP_NUM_THREADS",
                    "MPLBACKEND",
                ]
            }
            | ({"UV_PROJECT_ENVIRONMENT": ".verify-venv"} if name == "clean_install" else {}),
            "duration_seconds": time.perf_counter() - start,
            "summary": clean[-1800:],
            "log": f"results/acceptance/{name}.log",
            "source_sha256": snapshot["source_sha256"],
        }
        records.append(record)
        (output / "checks.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "recorded_at": datetime.now(UTC).isoformat(),
                    "source": snapshot,
                    "checks": records,
                    "status": "running",
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n"
        )
        print(f"{name}: {record['status']}", flush=True)
    records += [
        {
            "name": "docker_build_and_run",
            "command": ["docker build -t capprune:local .", "docker run --rm capprune:local"],
            "status": "not_run",
            "reason": "Docker executable absent / Docker 未安装",
            "source_sha256": snapshot["source_sha256"],
        },
        {
            "name": "remote_ci",
            "command": [],
            "status": "not_run",
            "reason": "No external push or publication / 未推送或公开发布",
            "source_sha256": snapshot["source_sha256"],
        },
    ]
    data = {
        "schema_version": 1,
        "recorded_at": datetime.now(UTC).isoformat(),
        "source": snapshot,
        "checks": records,
    }
    (output / "checks.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return int(any(r["status"] == "failed" for r in records))


if __name__ == "__main__":
    raise SystemExit(main())
