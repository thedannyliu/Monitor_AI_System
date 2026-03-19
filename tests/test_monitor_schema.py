from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from eval.assumptions import assumption_metrics
from monitoring.backends import HeuristicMonitorBackend, _coerce_report
from monitoring.schema import validate_monitor_report


class MonitorSchemaTest(unittest.TestCase):
    def test_heuristic_report_validates(self) -> None:
        backend = HeuristicMonitorBackend()
        task = {
            "task_id": "self-portfolio-001",
            "benchmark": "self_bench",
            "redacted_spec": "Build a personal portfolio website with a way for visitors to contact the owner.",
        }
        report = backend.generate_report(task, {"schema_version": "v1"})
        validate_monitor_report(report)
        self.assertGreaterEqual(len(report["assumptions"]), 1)

    def test_assumption_metrics_counts_matches(self) -> None:
        predicted = [
            {"statement": "The contact feature likely requires a real form instead of only a mailto link."}
        ]
        gold = [
            {"statement": "The contact feature must be a real submission form rather than only a mailto link."}
        ]
        metrics = assumption_metrics(predicted, gold)
        self.assertEqual(metrics["tp"], 1)
        self.assertEqual(metrics["fp"], 0)
        self.assertEqual(metrics["fn"], 0)

    def test_openai_near_miss_payload_is_normalized(self) -> None:
        task = {
            "task_id": "self-portfolio-001",
            "benchmark": "self_bench",
            "redacted_spec": "Build a portfolio website with a way for visitors to contact the owner.",
        }
        raw = {
            "hidden_assumptions": [
                {
                    "assumption": "The contact feature should use a real form.",
                    "impact": "A mailto link may not satisfy the intended workflow.",
                }
            ]
        }
        report = _coerce_report(task, raw)
        validate_monitor_report(report)
        self.assertEqual(report["task_id"], task["task_id"])
        self.assertEqual(report["benchmark"], task["benchmark"])
        self.assertEqual(report["spec_variant"], "redacted")
        self.assertEqual(report["assumptions"][0]["id"], "A1")


if __name__ == "__main__":
    unittest.main()
