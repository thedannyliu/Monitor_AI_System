from __future__ import annotations

import json
from typing import Any, Dict, List


SYSTEM_PROMPT = (
    "You are an auditing module for coding agents. "
    "Given a redacted task specification, identify hidden assumptions that may affect "
    "implementation choices, constraints, or validation. "
    "Return a single JSON object only. Do not wrap it in markdown fences. "
    "Use the exact top-level keys and nested keys requested by the schema. "
    "Do not invent speculative features that are not grounded in the redacted task."
)


def build_monitor_messages(task: Dict[str, Any], schema_hint: Dict[str, Any]) -> List[Dict[str, str]]:
    user_payload = {
        "task_id": task["task_id"],
        "benchmark": task["benchmark"],
        "task_summary": task["redacted_spec"],
        "output_requirements": {
            "top_level_keys": [
                "task_id",
                "benchmark",
                "spec_variant",
                "task_summary",
                "assumptions",
                "open_questions",
                "monitor_notes",
                "schema_version",
            ],
            "assumption_item_keys": [
                "id",
                "statement",
                "type",
                "evidence",
                "risk_if_wrong",
                "needs_confirmation",
                "confidence",
                "proposed_resolution",
                "linked_decisions",
            ],
            "open_question_keys": [
                "id",
                "question",
                "related_assumptions",
                "priority",
            ],
            "monitor_note_keys": [
                "category",
                "message",
            ],
            "allowed_assumption_types": [
                "Functional",
                "Implementation",
                "Environment",
                "Validation",
                "NonFunctional",
            ],
            "allowed_priorities": ["high", "medium", "low"],
            "allowed_note_categories": [
                "coverage_warning",
                "execution_risk",
                "context_gap",
            ],
            "constraints": [
                "spec_variant must be exactly 'redacted'",
                "schema_version must be exactly 'v1'",
                "Return between 2 and 4 assumptions when the task is underspecified",
                "Every assumption must have at least one evidence string",
                "confidence must be a number between 0.0 and 1.0",
            ],
        },
        "schema_hint": schema_hint,
    }
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=True, indent=2)},
    ]
