"""Check local links, bilingual pairs and shared tables. / 检查本地链接、双语对应和共享表格。"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    errors = []
    docs = [ROOT / "README.md", ROOT / "README_zh.md"]
    docs += sorted((ROOT / "docs").rglob("*.md"))
    docs += [
        ROOT / "CONTRIBUTING.md",
        ROOT / "CONTRIBUTING_zh.md",
        ROOT / "SECURITY.md",
        ROOT / "SECURITY_zh.md",
        ROOT / "NOTICE.md",
        ROOT / "NOTICE_zh.md",
    ]
    for path in docs:
        if not path.exists():
            errors.append(f"Missing / 缺失: {path.name}")
            continue
        text = path.read_text()
        if text.count("```") % 2:
            errors.append(f"Unclosed fence / 代码块未闭合: {path.name}")
        for target in re.findall(r"\]\(([^)]+)\)", text):
            if "://" in target or target.startswith("#"):
                continue
            target = target.split("#")[0]
            if not (path.parent / target).exists():
                errors.append(f"Broken / 失效: {path.relative_to(ROOT)} -> {target}")
        if path.parent.name in {"en", "zh"}:
            other = "zh" if path.parent.name == "en" else "en"
            if not (path.parent.parent / other / path.name).exists():
                errors.append(f"Missing translation / 缺少翻译: {path.name}")
    tables = [p.read_text() for p in [ROOT / "README.md", ROOT / "README_zh.md"] if p.exists()]
    numbers = [re.findall(r"^\| .*\d.*\|$", t, re.M) for t in tables]
    reference_table = ROOT / "results/analysis/table_en.md"
    if reference_table.exists():
        rows = re.findall(r"^\| .*\d.*\|$", reference_table.read_text(), re.M)
        for text in tables:
            if not all(row in text for row in rows):
                errors.append("README differs from generated results / README 与生成结果不符")
    if len(numbers) == 2 and numbers[0] != numbers[1]:
        errors.append("README measured tables differ / README 实测表不一致")
    if errors:
        raise SystemExit("\n".join(errors))
    for snippet in re.findall(r"```python\n(.*?)```", (ROOT / "README.md").read_text(), re.S):
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run([sys.executable, "-c", snippet], cwd=directory, check=True)
    print(
        f"{len(docs)} documents checked; pairs, links and examples valid / 双语对应、链接和示例通过"
    )


if __name__ == "__main__":
    main()
