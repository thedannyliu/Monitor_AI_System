from __future__ import annotations

from typing import Any, Dict, List

from eval.assumptions import normalize_statement


def build_oracle_review(report: Dict[str, Any], gold_assumptions: List[Dict[str, Any]]) -> Dict[str, Any]:
    gold_map = {normalize_statement(item["statement"]): item for item in gold_assumptions}
    review_actions = []
    covered = set()

    for assumption in report["assumptions"]:
        key = normalize_statement(assumption["statement"])
        if key in gold_map:
            covered.add(key)
            review_actions.append({"action": "accept", "assumption_id": assumption["id"]})
        else:
            review_actions.append(
                {
                    "action": "reject",
                    "assumption_id": assumption["id"],
                    "reason": "Not supported by the curated gold assumptions",
                }
            )

    next_index = len(report["assumptions"]) + 1
    for key, assumption in gold_map.items():
        if key in covered:
            continue
        review_actions.append(
            {
                "action": "add",
                "new_assumption": {
                    "id": f"A{next_index}",
                    "statement": assumption["statement"],
                    "type": assumption["type"],
                    "reason": "Missing from monitor output but present in the gold assumptions",
                },
            }
        )
        next_index += 1

    return {
        "task_id": report["task_id"],
        "benchmark": report["benchmark"],
        "review_actions": review_actions,
    }


def build_revised_spec(task: Dict[str, Any], review: Dict[str, Any], report: Dict[str, Any]) -> Dict[str, Any]:
    confirmed_assumptions = []
    rejected_assumptions = []
    execution_constraints = []

    report_map = {item["id"]: item["statement"] for item in report.get("assumptions", [])}
    for action in review["review_actions"]:
        name = action["action"]
        if name == "accept":
            assumption_id = action["assumption_id"]
            if assumption_id in report_map:
                confirmed_assumptions.append(report_map[assumption_id])
        elif name == "reject":
            assumption_id = action["assumption_id"]
            if assumption_id in report_map:
                rejected_assumptions.append(report_map[assumption_id])
        elif name == "add":
            confirmed_assumptions.append(action["new_assumption"]["statement"])

    execution_constraints.extend(confirmed_assumptions)
    return {
        "task_id": task["task_id"],
        "benchmark": task["benchmark"],
        "base_spec": task["redacted_spec"],
        "confirmed_assumptions": confirmed_assumptions,
        "rejected_assumptions": rejected_assumptions,
        "execution_constraints": execution_constraints,
    }
