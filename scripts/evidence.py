"""Portable provenance without identities or private paths. / 不含身份及私人路径的溯源。"""

from __future__ import annotations

import hashlib
import importlib.metadata
import os
import platform
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
from threadpoolctl import threadpool_info

ROOT = Path(__file__).resolve().parents[1]


def source_snapshot() -> dict[str, Any]:
    paths = sorted(
        list(ROOT.glob("src/**/*.py"))
        + list(ROOT.glob("scripts/*.py"))
        + list(ROOT.glob("tests/*.py"))
        + list(ROOT.glob("configs/*.json"))
        + [ROOT / "benchmark.py", ROOT / "pyproject.toml", ROOT / "uv.lock"]
    )
    files = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in paths
        if p.is_file()
    }
    digest = hashlib.sha256("\n".join(f"{k} {v}" for k, v in files.items()).encode()).hexdigest()
    try:
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL, text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        revision = None
    return {"git_revision": revision, "source_sha256": digest, "files": files}


def environment() -> dict[str, Any]:
    cpu = platform.processor() or platform.machine()
    if platform.system() == "Darwin":
        cpu = subprocess.check_output(
            ["sysctl", "-n", "machdep.cpu.brand_string"], text=True
        ).strip()
    pools = [{k: v for k, v in item.items() if k != "filepath"} for item in threadpool_info()]
    return {
        "os": platform.system(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
        "cpu": cpu,
        "python": platform.python_version(),
        "numpy_blas": {
            k: np.__config__.CONFIG["Build Dependencies"]["blas"].get(k)
            for k in ["name", "version", "found", "detection method"]
        },
        "requested_thread_environment": {
            name: os.environ.get(name)
            for name in ["VECLIB_MAXIMUM_THREADS", "OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS"]
        },
        "thread_limitation": (
            "Accelerate actual thread count is not introspectable via threadpoolctl; "
            "its maximum is requested through VECLIB_MAXIMUM_THREADS "
            "before NumPy import."
        ),
        "threadpools": pools,
        "packages": {
            name: importlib.metadata.version(name)
            for name in ["numpy", "scipy", "scikit-learn", "threadpoolctl", "psutil"]
        },
    }
