#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from agents.openai_agent import OpenAICompatibleCodingAgent
from benchmarks.tasks import load_manifest
from monitoring.review import build_oracle_review, build_revised_spec
from monitoring.schema import dump_json, load_json


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
    parser.add_argument("--monitor-results", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--model-name", default="Qwen/Qwen2.5-Coder-7B-Instruct")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    agent = OpenAICompatibleCodingAgent(args.base_url, args.model_name)
    tasks = []
    for manifest in [args.self_manifest, args.fea_manifest, args.swe_manifest]:
        tasks.extend(load_manifest(manifest))

    output_dir = Path(args.output_dir)
    monitor_root = Path(args.monitor_results)

    for task in tasks:
        for condition_name, spec_variant, use_monitor in CONDITIONS:
            spec_text = task["redacted_spec"] if spec_variant == "redacted" else task["full_spec"]
            if use_monitor:
                report_path = monitor_root / task["benchmark"] / condition_name / task["task_id"] / "monitor_report.json"
                report = load_json(report_path)
                review = build_oracle_review(report, task["gold_assumptions"])
                revised_spec = build_revised_spec(task, review, report)
                spec_text = "\n".join([task["redacted_spec"], "", "Confirmed constraints:"] + revised_spec["execution_constraints"])

            artifact = agent.generate_execution_artifact(task, condition_name, spec_text)
            dump_json(output_dir / task["benchmark"] / condition_name / f"{task['task_id']}.execution.json", artifact)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
