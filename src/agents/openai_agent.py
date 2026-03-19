from __future__ import annotations

import json
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
            return json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise AgentExecutionError("Agent backend did not return valid JSON") from exc
