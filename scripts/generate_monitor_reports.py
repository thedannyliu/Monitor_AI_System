#!/usr/bin/python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from benchmarks.tasks import load_manifest
from monitoring.backends import HeuristicMonitorBackend, OpenAICompatibleBackend
from monitoring.schema import dump_json, validate_monitor_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--backend", choices=["heuristic", "openai"], default="heuristic")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--model-name", default="Qwen/Qwen2.5-Coder-7B-Instruct")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    backend = (
        HeuristicMonitorBackend()
        if args.backend == "heuristic"
        else OpenAICompatibleBackend(args.base_url, args.model_name)
    )
    schema_hint = {
        "required_fields": [
            "task_id",
            "benchmark",
            "spec_variant",
            "task_summary",
            "assumptions",
            "open_questions",
            "monitor_notes",
            "schema_version",
        ]
    }

    output_dir = Path(args.output_dir)
    for task in load_manifest(args.manifest):
        report = backend.generate_report(task, schema_hint)
        validate_monitor_report(report)
        dump_json(output_dir / f"{task['task_id']}.report.json", report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
