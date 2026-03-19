#!/usr/bin/python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from benchmarks.tasks import load_manifest
from eval.assumptions import assumption_metrics
from monitoring.backends import HeuristicMonitorBackend, OpenAICompatibleBackend
from monitoring.review import build_oracle_review, build_revised_spec
from monitoring.schema import dump_json, validate_monitor_report


CONDITIONS = [
    ("direct_redacted", "redacted", False),
    ("direct_full", "full", False),
    ("monitor_then_act", "redacted", True),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-manifest", required=True)
    parser.add_argument("--fea-manifest", required=True)
    parser.add_argument("--swe-manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--backend", choices=["heuristic", "openai"], default="heuristic")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--model-name", default="Qwen2.5-Coder-7B-Instruct")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    backend = (
        HeuristicMonitorBackend()
        if args.backend == "heuristic"
        else OpenAICompatibleBackend(args.base_url, args.model_name)
    )
    schema_hint = {"schema_version": "v1"}
    tasks = []
    for manifest in [args.self_manifest, args.fea_manifest, args.swe_manifest]:
        tasks.extend(load_manifest(manifest))

    output_dir = Path(args.output_dir)
    summary_rows: List[Dict[str, object]] = []
    monitor_scores: List[Dict[str, float]] = []

    for task in tasks:
        benchmark_dir = output_dir / task["benchmark"]
        for condition_name, spec_variant, use_monitor in CONDITIONS:
            task_dir = benchmark_dir / condition_name / task["task_id"]
            task_dir.mkdir(parents=True, exist_ok=True)
            spec_text = task["redacted_spec"] if spec_variant == "redacted" else task["full_spec"]
            condition_payload = {
                "task_id": task["task_id"],
                "benchmark": task["benchmark"],
                "condition": condition_name,
                "spec_variant": spec_variant,
                "spec_text": spec_text,
                "execution_status": "prepared",
            }
            dump_json(task_dir / "input.json", condition_payload)

            row = {
                "benchmark": task["benchmark"],
                "task_id": task["task_id"],
                "condition": condition_name,
                "spec_variant": spec_variant,
                "execution_status": "prepared",
            }

            if use_monitor:
                report = backend.generate_report(task, schema_hint)
                validate_monitor_report(report)
                dump_json(task_dir / "monitor_report.json", report)
                review = build_oracle_review(report, task["gold_assumptions"])
                dump_json(task_dir / "oracle_review.json", review)
                revised_spec = build_revised_spec(task, review, report)
                dump_json(task_dir / "revised_spec.json", revised_spec)
                metrics = assumption_metrics(report["assumptions"], task["gold_assumptions"])
                dump_json(task_dir / "assumption_metrics.json", metrics)
                row.update(metrics)
                monitor_scores.append(metrics)
            summary_rows.append(row)

    summary = {
        "total_runs": len(summary_rows),
        "monitor_runs": len(monitor_scores),
        "average_precision": _average(monitor_scores, "precision"),
        "average_recall": _average(monitor_scores, "recall"),
        "average_f1": _average(monitor_scores, "f1"),
        "runs": summary_rows,
    }
    dump_json(output_dir / "pilot_summary.json", summary)
    print(json.dumps(summary, indent=2))
    return 0


def _average(rows: List[Dict[str, float]], key: str) -> float:
    if not rows:
        return 0.0
    return round(sum(float(row[key]) for row in rows) / len(rows), 4)


if __name__ == "__main__":
    raise SystemExit(main())
