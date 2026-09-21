#!/usr/bin/env python3
"""Generate bilingual result tables and a plot. / 自动生成双语结果表和图。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def summarize(record: dict) -> list[dict]:
    rows = []
    for case in record["cases"]:
        if case["status"] != "passed":
            rows.append({"case": case["name"], "status": case["status"]})
            continue
        row = {
            "case": case["name"],
            "status": "passed",
            "n": case["actual_shape"][0],
            "build_ms": case["build_ns"] / 1e6,
            "index_mib": case["index_array_bytes"] / 2**20,
        }
        for mode in record["protocol"]["modes"]:
            samples = [s for s in case["samples"] if s["mode"] == mode]
            times = np.asarray([s["elapsed_ns"] / 1e6 for s in samples])
            row[mode] = {
                "median_ms": float(np.median(times)),
                "q25_ms": float(np.quantile(times, 0.25)),
                "q75_ms": float(np.quantile(times, 0.75)),
                "samples": len(samples),
                "throughput_qps": float(len(times) / (times.sum() / 1000)),
                "mean_evaluated_fraction": float(
                    np.mean([s["evaluated_vectors"] / row["n"] for s in samples])
                ),
                "repeat_medians_ms": [
                    float(np.median([s["elapsed_ns"] / 1e6 for s in samples if s["repeat"] == r]))
                    for r in range(record["protocol"]["repetitions"])
                ],
            }
        row["speedup"] = row["scan"]["median_ms"] / row["pruned"]["median_ms"]
        saving = row["scan"]["median_ms"] - row["pruned"]["median_ms"]
        row["build_break_even_queries"] = (
            int(np.ceil(row["build_ms"] / saving)) if saving > 0 else None
        )
        rows.append(row)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("results/analysis"))
    args = parser.parse_args()
    raw = json.loads(args.input.read_text())
    rows = summarize(raw)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "summary.json").write_text(
        json.dumps({"run_id": raw["run_id"], "source": raw["source"], "rows": rows}, indent=2)
        + "\n"
    )
    for lang in ["en", "zh"]:
        intro = (
            "Measured results; requested one CPU thread, float64, online batch=1. "
            "Medians include all repeats; no tail-latency claim."
            if lang == "en"
            else (
                "实测结果；CPU 线程上限请求为 1、float64、在线批大小 1。"
                "中位数包含全部重复，不作尾延迟结论。"
            )
        )
        text = intro + "\n\n"
        text += (
            "| Case / 场景 | Scan ms | Blocked ms | Pruned ms | "
            "Speedup / 加速比 | Scored / 评分比例 | Build ms |\n"
        )
        text += "|---|---:|---:|---:|---:|---:|---:|\n"
        for row in rows:
            if row["status"] != "passed":
                text += f"| {row['case']} | failed | — | — | — | — | — |\n"
            else:
                text += (
                    f"| {row['case']} | {row['scan']['median_ms']:.4f} | "
                    f"{row['blocked']['median_ms']:.4f} | {row['pruned']['median_ms']:.4f} | "
                    f"{row['speedup']:.2f}× | {row['pruned']['mean_evaluated_fraction']:.1%} | "
                    f"{row['build_ms']:.1f} |\n"
                )
        (args.output_dir / f"table_{lang}.md").write_text(text)
    valid = [r for r in rows if r["status"] == "passed"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
    labels = [r["case"] for r in valid]
    axes[0].barh(labels, [r["speedup"] for r in valid], color="#087f8c")
    axes[0].axvline(1, color="black", linestyle="--", linewidth=1)
    axes[0].set_xlabel("Scan median / pruned median (higher is better)")
    axes[1].barh(
        labels, [100 * r["pruned"]["mean_evaluated_fraction"] for r in valid], color="#bd582c"
    )
    axes[1].set_xlabel("Vectors scored (%)")
    axes[1].set_xlim(0, 105)
    axes[1].set_yticklabels([])
    fig.savefig(args.output_dir / "benchmark.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
