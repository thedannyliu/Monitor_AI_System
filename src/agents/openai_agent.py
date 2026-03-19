from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List


class AgentExecutionError(RuntimeError):
    """Raised when the coding agent backend fails."""


class OpenAICompatibleCodingAgent:
    def __init__(self, base_url: str, model_name: str, timeout: int = 180):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout

    def generate_execution_artifact(self, task: Dict[str, Any], condition: str, spec_text: str) -> Dict[str, Any]:
        system_prompt = (
            "You are a coding agent. Produce a concise execution plan and an initial patch strategy "
            "for the given task specification. Return valid JSON only."
        )
        user_payload = {
            "task_id": task["task_id"],
            "benchmark": task["benchmark"],
            "condition": condition,
            "spec_text": spec_text,
            "required_output": {
                "plan_steps": ["string"],
                "files_to_modify": ["string"],
                "test_strategy": ["string"],
                "assumption_sensitive_areas": ["string"],
            },
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=True, indent=2)},
            ],
            "temperature": 0.0,
            "top_p": 1.0,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            url=f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise AgentExecutionError(f"Agent backend request failed: {exc}") from exc
        try:
            content = raw["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise AgentExecutionError("Agent backend did not return valid JSON") from exc
        cleaned = _strip_code_fences(content)
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise AgentExecutionError("Agent backend did not return valid JSON") from exc
        return _coerce_execution_artifact(parsed)


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    return text


def _coerce_execution_artifact(parsed: Any) -> Dict[str, Any]:
    if not isinstance(parsed, dict):
        raise AgentExecutionError("Agent backend returned a non-object payload")

    artifact = {
        "plan_steps": _coerce_string_list(parsed.get("plan_steps") or parsed.get("steps") or parsed.get("plan")),
        "files_to_modify": _coerce_string_list(parsed.get("files_to_modify") or parsed.get("files") or parsed.get("files_to_change")),
        "test_strategy": _coerce_string_list(parsed.get("test_strategy") or parsed.get("tests") or parsed.get("validation")),
        "assumption_sensitive_areas": _coerce_string_list(
            parsed.get("assumption_sensitive_areas") or parsed.get("risks") or parsed.get("assumptions")
        ),
    }
    if not artifact["plan_steps"]:
        artifact["plan_steps"] = ["Review the task and identify the minimum code changes required."]
    if not artifact["files_to_modify"]:
        artifact["files_to_modify"] = ["To be determined after repository inspection."]
    if not artifact["test_strategy"]:
        artifact["test_strategy"] = ["Run the benchmark's existing test suite covering the changed behavior."]
    if not artifact["assumption_sensitive_areas"]:
        artifact["assumption_sensitive_areas"] = ["Repository-specific integration details not fully specified by the prompt."]
    return artifact


def _coerce_string_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []
