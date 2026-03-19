from __future__ import annotations

import json
from typing import Any, Dict, List


SYSTEM_PROMPT = (
    "You are an auditing module for coding agents. "
    "Given a redacted task specification, identify hidden assumptions that may affect "
    "implementation choices, constraints, or validation. "
    "Return a single JSON object only. Do not wrap it in markdown fences. "
    "Use the exact top-level keys and nested keys requested by the schema. "
    "Do not invent speculative features that are not grounded in the redacted task. "
    "A hidden assumption must be an omitted constraint, deliverable, compatibility rule, "
    "API detail, validation rule, deployment requirement, or exact behavior that is NOT "
    "already stated explicitly in the redacted task."
)


def build_monitor_messages(task: Dict[str, Any], schema_hint: Dict[str, Any]) -> List[Dict[str, str]]:
    benchmark_guidance = _build_benchmark_guidance(task)
    user_payload = {
        "task_id": task["task_id"],
        "benchmark": task["benchmark"],
        "task_summary": task["redacted_spec"],
        "benchmark_guidance": benchmark_guidance,
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
                "Return only hidden assumptions that are missing from the redacted task",
                "Do not restate the bug report or feature request itself",
                "Avoid generic assumptions such as internal users, HTML/CSS/JS, HTTPS, CPU, memory, scalability, or security unless directly implied by the task text",
                "Prefer omitted constraints like exact API names, storage backends, file formats, validation rules, backward compatibility, tests/docs deliverables, deployment targets, or explicit UX filters",
                "Return between 2 and 5 assumptions when the task is underspecified",
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


def _build_benchmark_guidance(task: Dict[str, Any]) -> Dict[str, Any]:
    benchmark = task["benchmark"]
    if benchmark == "self_bench":
        return {
            "focus_on": [
                "storage backend or persistence requirements",
                "input modality or data format",
                "pagination, filtering, or ordering behavior",
                "validation rules and test coverage",
                "deployment or UI constraints",
                "small but explicit feature-scope items omitted from the prompt",
            ],
            "good_examples": [
                "The list endpoint may require pagination.",
                "Uploaded dashboard data may need to persist in SQLite.",
                "The site may need to remain static with no runtime database.",
            ],
            "bad_examples": [
                "The API is probably internal only.",
                "The project will use HTML, CSS, and JavaScript.",
                "The system should use HTTPS.",
            ],
        }
    if benchmark == "fea_bench":
        return {
            "focus_on": [
                "exact API placement or function naming",
                "compatibility with existing flags or behavior",
                "required tests or documentation updates",
                "standards or schema compliance",
                "exact output semantics omitted from the redacted text",
            ],
            "good_examples": [
                "An existing opt-out flag may need to preserve prior behavior.",
                "The feature may need to live on a specific class or module path.",
                "The change may require tests and docs, not only code.",
            ],
            "bad_examples": [
                "The system has enough CPU and memory.",
                "The current bug interrupts users.",
                "The codebase probably has no similar feature.",
            ],
        }
    return {
        "focus_on": [
            "exact semantics hidden by removed examples",
            "backward compatibility targets",
            "case sensitivity, parsing, or matrix behavior",
            "implementation clues that explain the failure mechanism",
        ],
        "good_examples": [
            "Lowercase commands may need to parse successfully.",
            "The fix may need to preserve behavior from a previous version.",
            "Issue examples may define the intended matrix semantics.",
        ],
        "bad_examples": [
            "The function should behave correctly.",
            "The current implementation has a bug.",
            "The code should be refactored carefully.",
        ],
    }
