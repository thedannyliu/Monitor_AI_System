from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


ALLOWED_BENCHMARKS = {"self_bench", "fea_bench", "swe_bench"}
ALLOWED_TYPES = {
    "Functional",
    "Implementation",
    "Environment",
    "Validation",
    "NonFunctional",
}
ALLOWED_PRIORITIES = {"high", "medium", "low"}
ALLOWED_NOTE_CATEGORIES = {"coverage_warning", "execution_risk", "context_gap"}


class SchemaValidationError(ValueError):
    """Raised when a monitor report does not match the expected schema."""


@dataclass
class Assumption:
    id: str
    statement: str
    type: str
    evidence: List[str]
    risk_if_wrong: str
    needs_confirmation: bool
    confidence: float
    proposed_resolution: str
    linked_decisions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "statement": self.statement,
            "type": self.type,
            "evidence": self.evidence,
            "risk_if_wrong": self.risk_if_wrong,
            "needs_confirmation": self.needs_confirmation,
            "confidence": self.confidence,
            "proposed_resolution": self.proposed_resolution,
            "linked_decisions": self.linked_decisions,
        }


@dataclass
class OpenQuestion:
    id: str
    question: str
    related_assumptions: List[str]
    priority: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "related_assumptions": self.related_assumptions,
            "priority": self.priority,
        }


@dataclass
class MonitorNote:
    category: str
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {"category": self.category, "message": self.message}


@dataclass
class MonitorReport:
    task_id: str
    benchmark: str
    spec_variant: str
    task_summary: str
    assumptions: List[Assumption]
    open_questions: List[OpenQuestion]
    monitor_notes: List[MonitorNote]
    schema_version: str = "v1"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "benchmark": self.benchmark,
            "spec_variant": self.spec_variant,
            "task_summary": self.task_summary,
            "assumptions": [item.to_dict() for item in self.assumptions],
            "open_questions": [item.to_dict() for item in self.open_questions],
            "monitor_notes": [item.to_dict() for item in self.monitor_notes],
            "schema_version": self.schema_version,
        }


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def dump_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=True)
        handle.write("\n")


def validate_monitor_report(report: Dict[str, Any]) -> None:
    required = {
        "task_id",
        "benchmark",
        "spec_variant",
        "task_summary",
        "assumptions",
        "open_questions",
        "monitor_notes",
        "schema_version",
    }
    missing = sorted(required.difference(report.keys()))
    if missing:
        raise SchemaValidationError(f"Missing report fields: {missing}")
    if report["benchmark"] not in ALLOWED_BENCHMARKS:
        raise SchemaValidationError(f"Unsupported benchmark: {report['benchmark']}")
    if report["spec_variant"] != "redacted":
        raise SchemaValidationError("spec_variant must be 'redacted'")
    if not isinstance(report["assumptions"], list):
        raise SchemaValidationError("assumptions must be a list")
    if not isinstance(report["open_questions"], list):
        raise SchemaValidationError("open_questions must be a list")
    if not isinstance(report["monitor_notes"], list):
        raise SchemaValidationError("monitor_notes must be a list")

    seen_ids = set()
    for item in report["assumptions"]:
        _validate_assumption(item, seen_ids)
    for item in report["open_questions"]:
        _validate_open_question(item)
    for item in report["monitor_notes"]:
        _validate_monitor_note(item)


def _validate_assumption(item: Dict[str, Any], seen_ids: set) -> None:
    required = {
        "id",
        "statement",
        "type",
        "evidence",
        "risk_if_wrong",
        "needs_confirmation",
        "confidence",
        "proposed_resolution",
    }
    missing = sorted(required.difference(item.keys()))
    if missing:
        raise SchemaValidationError(f"Assumption missing fields: {missing}")
    if item["id"] in seen_ids:
        raise SchemaValidationError(f"Duplicate assumption id: {item['id']}")
    seen_ids.add(item["id"])
    if item["type"] not in ALLOWED_TYPES:
        raise SchemaValidationError(f"Unsupported assumption type: {item['type']}")
    if not isinstance(item["evidence"], list) or not item["evidence"]:
        raise SchemaValidationError("evidence must be a non-empty list")
    if not isinstance(item["needs_confirmation"], bool):
        raise SchemaValidationError("needs_confirmation must be a boolean")
    if not isinstance(item["confidence"], (float, int)):
        raise SchemaValidationError("confidence must be numeric")
    if not 0.0 <= float(item["confidence"]) <= 1.0:
        raise SchemaValidationError("confidence must be between 0 and 1")


def _validate_open_question(item: Dict[str, Any]) -> None:
    required = {"id", "question", "related_assumptions", "priority"}
    missing = sorted(required.difference(item.keys()))
    if missing:
        raise SchemaValidationError(f"Open question missing fields: {missing}")
    if item["priority"] not in ALLOWED_PRIORITIES:
        raise SchemaValidationError(f"Unsupported priority: {item['priority']}")
    if not isinstance(item["related_assumptions"], list):
        raise SchemaValidationError("related_assumptions must be a list")


def _validate_monitor_note(item: Dict[str, Any]) -> None:
    required = {"category", "message"}
    missing = sorted(required.difference(item.keys()))
    if missing:
        raise SchemaValidationError(f"Monitor note missing fields: {missing}")
    if item["category"] not in ALLOWED_NOTE_CATEGORIES:
        raise SchemaValidationError(f"Unsupported monitor note category: {item['category']}")
