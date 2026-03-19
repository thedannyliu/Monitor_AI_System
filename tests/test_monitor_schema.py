from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from eval.assumptions import assumption_metrics
from monitoring.backends import HeuristicMonitorBackend
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


if __name__ == "__main__":
    unittest.main()
