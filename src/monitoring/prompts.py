from __future__ import annotations

import json
from typing import Any, Dict, List


SYSTEM_PROMPT = (
    "You are an auditing module for coding agents. "
    "Given a redacted task specification, identify hidden assumptions that may affect "
    "implementation choices, constraints, or validation. "
    "Return valid JSON only and follow the provided schema exactly."
)


def build_monitor_messages(task: Dict[str, Any], schema_hint: Dict[str, Any]) -> List[Dict[str, str]]:
    user_payload = {
        "task_id": task["task_id"],
        "benchmark": task["benchmark"],
        "task_summary": task["redacted_spec"],
        "output_schema": schema_hint,
    }
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=True, indent=2)},
    ]
