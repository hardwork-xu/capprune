"""Audit public files and package contents. / 检查公开文件与构建产物。"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "private_path": re.compile(r"/(?:Users|home)/[A-Za-z][^\s/'\"<>]*/"),
    "email": re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
    "token": re.compile(r"(?:ghp_|github_pat_|sk-proj-)[A-Za-z0-9_]{20,}"),
}


def inspect(name: str, data: bytes, findings: list[str]) -> None:
    if name.endswith((".png", ".jpg", ".npz", ".npy", ".pyc")):
        return
    text = data.decode("utf-8", errors="replace")
    for kind, pattern in PATTERNS.items():
        if pattern.search(text):
            findings.append(f"{kind}: {name}")


def main() -> None:
    # The Git control file/metadata is deliberately excluded. / 明确排除 Git 控制文件及元数据。
    listed = (
        subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT
        )
        .decode()
        .split("\0")
    )
    files = sorted({p for p in listed if p and p != "results/acceptance/audit.json"})
    findings: list[str] = []
    manifest = {}
    for name in files:
        data = (ROOT / name).read_bytes()
        inspect(name, data, findings)
        manifest[name] = hashlib.sha256(data).hexdigest()
    packages = {}
    for package in sorted((ROOT / "dist").glob("*")):
        if package.suffix == ".whl":
            with zipfile.ZipFile(package) as archive:
                for name in archive.namelist():
                    inspect(name, archive.read(name), findings)
        elif package.name.endswith(".tar.gz"):
            with tarfile.open(package) as archive:
                for member in archive.getmembers():
                    if member.isfile():
                        stream = archive.extractfile(member)
                        assert stream is not None
                        inspect(member.name, stream.read(), findings)
        else:
            continue
        packages[package.name] = hashlib.sha256(package.read_bytes()).hexdigest()
    report = {
        "status": "passed" if not findings else "failed",
        "findings": findings,
        "scope": "tracked and unignored public files plus wheel/sdist; Git metadata excluded",
        "limitations": "Pattern scan and package inspection; not a guarantee against all secrets.",
        "files": manifest,
        "packages": packages,
    }
    output = ROOT / "results/acceptance/audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "files": len(files), "findings": findings}))
    if findings:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
