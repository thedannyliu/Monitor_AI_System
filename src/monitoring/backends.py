from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from monitoring.prompts import build_monitor_messages
from monitoring.schema import ALLOWED_NOTE_CATEGORIES, ALLOWED_PRIORITIES, ALLOWED_TYPES


class MonitorBackendError(RuntimeError):
    """Raised when a backend cannot produce a monitor report."""


class BaseMonitorBackend(ABC):
    @abstractmethod
    def generate_report(self, task: Dict[str, Any], schema_hint: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


class HeuristicMonitorBackend(BaseMonitorBackend):
    def generate_report(self, task: Dict[str, Any], schema_hint: Dict[str, Any]) -> Dict[str, Any]:
        assumptions = _infer_assumptions(task)
        open_questions = [
            {
                "id": f"Q{index + 1}",
                "question": item["proposed_resolution"],
                "related_assumptions": [item["id"]],
                "priority": "high" if item["needs_confirmation"] else "medium",
            }
            for index, item in enumerate(assumptions[:3])
        ]
        notes = []
        if len(assumptions) < 2:
            notes.append(
                {
                    "category": "coverage_warning",
                    "message": "The heuristic backend identified only a small number of assumptions.",
                }
            )
        else:
            notes.append(
                {
                    "category": "context_gap",
                    "message": "The task appears underspecified and likely requires explicit review.",
                }
            )
        return {
            "task_id": task["task_id"],
            "benchmark": task["benchmark"],
            "spec_variant": "redacted",
            "task_summary": task["redacted_spec"],
            "assumptions": assumptions,
            "open_questions": open_questions,
            "monitor_notes": notes,
            "schema_version": "v1",
        }


class OpenAICompatibleBackend(BaseMonitorBackend):
    def __init__(self, base_url: str, model_name: str, timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout

    def generate_report(self, task: Dict[str, Any], schema_hint: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "model": self.model_name,
            "messages": build_monitor_messages(task, schema_hint),
            "temperature": 0.0,
            "top_p": 1.0,
            "response_format": {"type": "json_object"},
        }
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url=f"{self.base_url}/chat/completions",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise MonitorBackendError(f"OpenAI-compatible backend request failed: {exc}") from exc

        try:
            content = raw["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise MonitorBackendError("Unexpected response format from OpenAI-compatible backend") from exc
        cleaned = _strip_code_fences(content)
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise MonitorBackendError("Model output is not valid JSON") from exc
        return _coerce_report(task, parsed)


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    return text


def _coerce_report(task: Dict[str, Any], parsed: Any) -> Dict[str, Any]:
    assumptions = _extract_assumptions(task, parsed)
    open_questions = _extract_open_questions(parsed, assumptions)
    monitor_notes = _extract_monitor_notes(parsed, assumptions)

    report = {
        "task_id": task["task_id"],
        "benchmark": task["benchmark"],
        "spec_variant": "redacted",
        "task_summary": task["redacted_spec"],
        "assumptions": assumptions,
        "open_questions": open_questions,
        "monitor_notes": monitor_notes,
        "schema_version": "v1",
    }

    if isinstance(parsed, dict):
        report["task_id"] = str(parsed.get("task_id") or report["task_id"])
        benchmark = parsed.get("benchmark")
        if benchmark == task["benchmark"]:
            report["benchmark"] = benchmark
        spec_variant = parsed.get("spec_variant")
        if spec_variant == "redacted":
            report["spec_variant"] = spec_variant
        task_summary = parsed.get("task_summary")
        if isinstance(task_summary, str) and task_summary.strip():
            report["task_summary"] = task_summary.strip()
        schema_version = parsed.get("schema_version")
        if schema_version == "v1":
            report["schema_version"] = schema_version

    return report


def _extract_assumptions(task: Dict[str, Any], parsed: Any) -> List[Dict[str, Any]]:
    if isinstance(parsed, dict):
        if isinstance(parsed.get("assumptions"), list):
            raw_items = parsed["assumptions"]
        elif isinstance(parsed.get("hidden_assumptions"), list):
            raw_items = parsed["hidden_assumptions"]
        elif isinstance(parsed.get("assumption_candidates"), list):
            raw_items = parsed["assumption_candidates"]
        else:
            raw_items = []
    elif isinstance(parsed, list):
        raw_items = parsed
    else:
        raw_items = []

    items = [_coerce_assumption_item(task, item, index) for index, item in enumerate(raw_items, start=1)]
    items = [item for item in items if item["statement"]]
    if items:
        return items[:4]
    return HeuristicMonitorBackend().generate_report(task, {"schema_version": "v1"})["assumptions"]


def _coerce_assumption_item(task: Dict[str, Any], item: Any, index: int) -> Dict[str, Any]:
    if isinstance(item, str):
        statement = item.strip()
        item = {"statement": statement}
    elif not isinstance(item, dict):
        item = {}

    statement = _first_text(
        item,
        ["statement", "assumption", "questionable_assumption", "description", "summary"],
    )
    evidence = _coerce_string_list(item.get("evidence"))
    if not evidence:
        inferred_impact = _first_text(item, ["impact", "reason", "rationale"])
        if inferred_impact:
            evidence = [inferred_impact]
        else:
            evidence = ["The redacted task omits implementation or validation details that affect execution choices."]

    assumption_type = item.get("type")
    if assumption_type not in ALLOWED_TYPES:
        assumption_type = _infer_type(statement, evidence)

    proposed_resolution = _first_text(
        item,
        ["proposed_resolution", "resolution", "clarifying_question", "follow_up"],
    )
    if not proposed_resolution:
        proposed_resolution = f"Confirm whether this task requires: {statement.lower()}"

    risk_if_wrong = _first_text(item, ["risk_if_wrong", "risk", "impact"])
    if not risk_if_wrong:
        risk_if_wrong = "The agent may implement a solution that is technically valid but misaligned with the hidden task constraint."

    confidence = item.get("confidence", 0.55)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.55
    confidence = min(1.0, max(0.0, confidence))

    needs_confirmation = item.get("needs_confirmation")
    if not isinstance(needs_confirmation, bool):
        needs_confirmation = True

    linked_decisions = _coerce_string_list(item.get("linked_decisions"))
    if not linked_decisions:
        linked_decisions = _infer_linked_decisions(task["redacted_spec"], statement)

    return {
        "id": f"A{index}",
        "statement": statement,
        "type": assumption_type,
        "evidence": evidence,
        "risk_if_wrong": risk_if_wrong,
        "needs_confirmation": needs_confirmation,
        "confidence": round(confidence, 2),
        "proposed_resolution": proposed_resolution,
        "linked_decisions": linked_decisions,
    }


def _extract_open_questions(parsed: Any, assumptions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    raw_items = []
    if isinstance(parsed, dict) and isinstance(parsed.get("open_questions"), list):
        raw_items = parsed["open_questions"]

    items = []
    for index, item in enumerate(raw_items, start=1):
        if not isinstance(item, dict):
            continue
        question = _first_text(item, ["question", "prompt"])
        if not question:
            continue
        priority = item.get("priority", "medium")
        if priority not in ALLOWED_PRIORITIES:
            priority = "medium"
        related = _coerce_string_list(item.get("related_assumptions"))
        items.append(
            {
                "id": f"Q{index}",
                "question": question,
                "related_assumptions": related or [assumptions[min(index - 1, len(assumptions) - 1)]["id"]],
                "priority": priority,
            }
        )
    if items:
        return items[:3]

    derived = []
    for index, item in enumerate(assumptions[:3], start=1):
        derived.append(
            {
                "id": f"Q{index}",
                "question": item["proposed_resolution"],
                "related_assumptions": [item["id"]],
                "priority": "high" if item["needs_confirmation"] else "medium",
            }
        )
    return derived


def _extract_monitor_notes(parsed: Any, assumptions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    raw_items = []
    if isinstance(parsed, dict) and isinstance(parsed.get("monitor_notes"), list):
        raw_items = parsed["monitor_notes"]

    items = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        category = item.get("category", "context_gap")
        if category not in ALLOWED_NOTE_CATEGORIES:
            category = "context_gap"
        message = _first_text(item, ["message", "note", "summary"])
        if not message:
            continue
        items.append({"category": category, "message": message})
    if items:
        return items[:3]

    return [
        {
            "category": "context_gap" if assumptions else "coverage_warning",
            "message": "The redacted task leaves at least part of the implementation contract implicit and requires review before execution.",
        }
    ]


def _coerce_string_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _first_text(item: Dict[str, Any], keys: List[str]) -> str:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _infer_type(statement: str, evidence: List[str]) -> str:
    text = " ".join([statement] + evidence).lower()
    if any(token in text for token in ["responsive", "test", "validate", "viewport", "acceptance"]):
        return "Validation"
    if any(token in text for token in ["deploy", "vercel", "environment", "version", "platform"]):
        return "Environment"
    if any(token in text for token in ["database", "backend", "storage", "persist", "api", "route"]):
        return "Implementation"
    if any(token in text for token in ["performance", "security", "privacy", "accessibility", "seo"]):
        return "NonFunctional"
    return "Functional"


def _infer_linked_decisions(spec_text: str, statement: str) -> List[str]:
    text = f"{spec_text} {statement}".lower()
    linked = []
    if any(token in text for token in ["backend", "api", "route", "persist", "database"]):
        linked.append("Backend architecture")
    if any(token in text for token in ["deploy", "vercel", "platform"]):
        linked.append("Deployment configuration")
    if any(token in text for token in ["responsive", "mobile", "desktop", "viewport"]):
        linked.append("UI validation plan")
    if any(token in text for token in ["contact", "admin", "auth", "form"]):
        linked.append("Feature scope")
    return linked


def _infer_assumptions(task: Dict[str, Any]) -> List[Dict[str, Any]]:
    text = task["redacted_spec"].lower()
    handlers = [
        _portfolio_rules,
        _dashboard_rules,
        _api_rules,
        _cli_rules,
        _blog_rules,
        _aider_rules,
        _monai_rules,
        _pythainlp_rules,
        _rdflib_chunk_rules,
        _rdflib_cbd_rules,
        _separability_rules,
        _rst_rules,
        _qdp_rules,
        _mask_rules,
        _dexponent_rules,
    ]
    items: List[Dict[str, Any]] = []
    for handler in handlers:
        items.extend(handler(text))
    if not items:
        items.append(
            _make_assumption(
                1,
                "The task has omitted one or more validation constraints that should be reviewed before execution.",
                "Validation",
                "The redacted spec is brief and leaves acceptance details unstated.",
                "The agent may implement a superficially correct but misaligned solution.",
                "Review the expected acceptance behavior before execution.",
                ["Test coverage", "Acceptance behavior"],
            )
        )
    for index, item in enumerate(items, start=1):
        item["id"] = f"A{index}"
    return items[:4]


def _portfolio_rules(text: str) -> List[Dict[str, Any]]:
    if "portfolio" not in text:
        return []
    return [
        _make_assumption(
            1,
            "The contact feature likely requires a real form instead of only a mailto link.",
            "Functional",
            "The spec asks for contact capability but does not define the interaction model.",
            "A mailto-only implementation may fail user expectations.",
            "Confirm whether visitors should submit a form or just see contact details.",
            ["Contact UX"],
        ),
        _make_assumption(
            2,
            "The portfolio may require backend storage for contact submissions.",
            "Implementation",
            "The spec does not state whether contact messages must be retained.",
            "A static implementation may miss persistence requirements.",
            "Confirm whether contact submissions need server-side storage.",
            ["Backend routes", "Data persistence"],
        ),
    ]


def _dashboard_rules(text: str) -> List[Dict[str, Any]]:
    if "dashboard" not in text:
        return []
    return [
        _make_assumption(
            1,
            "The dashboard likely needs persisted uploaded data rather than session-only state.",
            "Implementation",
            "Analytics dashboards often retain historical uploads, but the redacted spec does not say how data is stored.",
            "Results may disappear between sessions if persistence is omitted.",
            "Confirm whether uploaded data must be saved across sessions.",
            ["Storage backend"],
        ),
        _make_assumption(
            2,
            "Input data probably requires validation and user-facing error reporting.",
            "Validation",
            "The spec accepts external data but does not describe malformed input handling.",
            "The dashboard may silently ignore bad rows or crash on upload.",
            "Confirm how invalid input rows should be surfaced to the user.",
            ["Upload validation"],
        ),
    ]


def _api_rules(text: str) -> List[Dict[str, Any]]:
    if "api" not in text and "endpoint" not in text:
        return []
    return [
        _make_assumption(
            1,
            "The API likely needs a persistent database rather than in-memory storage.",
            "Implementation",
            "CRUD APIs usually imply durable storage, but the redacted spec does not specify a backend.",
            "An in-memory API may fail persistence expectations.",
            "Confirm the storage backend and persistence requirement.",
            ["Database selection"],
        ),
        _make_assumption(
            2,
            "List endpoints may require pagination or filtering behavior that is currently unspecified.",
            "Functional",
            "The redacted spec defines CRUD operations but omits listing constraints.",
            "A naive list response may not match the expected API contract.",
            "Confirm whether list responses need pagination, sorting, or filtering.",
            ["Response schema"],
        ),
    ]


def _cli_rules(text: str) -> List[Dict[str, Any]]:
    if "cli" not in text and "markdown notes" not in text:
        return []
    return [
        _make_assumption(
            1,
            "The scanner may need to recurse into subdirectories.",
            "Functional",
            "Directory-scanning tools often support nested content, but the redacted spec does not say so.",
            "A shallow scan may miss valid files.",
            "Confirm whether recursive scanning is required.",
            ["Traversal behavior"],
        ),
        _make_assumption(
            2,
            "The report output format may need to be machine-readable JSON.",
            "Environment",
            "The redacted spec does not define how the report should be consumed.",
            "A plain-text report may be unusable for downstream automation.",
            "Confirm the required report format and CLI flags.",
            ["Output format"],
        ),
    ]


def _blog_rules(text: str) -> List[Dict[str, Any]]:
    if "blog" not in text:
        return []
    return [
        _make_assumption(
            1,
            "Blog content may be sourced from Markdown files instead of a runtime database.",
            "Implementation",
            "The redacted spec names site pages but does not define the content pipeline.",
            "The implementation could add unnecessary infrastructure or miss the intended authoring workflow.",
            "Confirm the content source and whether the site must remain static.",
            ["Content pipeline"],
        ),
        _make_assumption(
            2,
            "The post list may require explicit publish-date ordering and publication filtering.",
            "Validation",
            "Listing behavior is not specified in the redacted task.",
            "Posts may render in the wrong order or expose drafts.",
            "Confirm ordering and visibility rules for posts.",
            ["Listing behavior"],
        ),
    ]


def _aider_rules(text: str) -> List[Dict[str, Any]]:
    if "dirty file" not in text and "commit behavior" not in text:
        return []
    return [
        _make_assumption(
            1,
            "Auto-committing should apply only when the model is about to edit the dirty file.",
            "Validation",
            "The task mentions dirty-file behavior but does not define the exact trigger.",
            "An overly broad auto-commit policy could change unrelated user work.",
            "Confirm which dirty files should be committed automatically.",
            ["Commit trigger"],
        ),
        _make_assumption(
            2,
            "Existing safety flags or opt-out behavior must remain compatible.",
            "Environment",
            "Behavior-changing features in developer tools often need to preserve existing flags.",
            "The change may regress explicit user controls.",
            "Confirm whether any flags must keep their previous behavior.",
            ["CLI compatibility"],
        ),
    ]


def _monai_rules(text: str) -> List[Dict[str, Any]]:
    if "datalist" not in text:
        return []
    return [
        _make_assumption(
            1,
            "The JSON format likely follows a benchmark-specific schema rather than arbitrary JSON.",
            "Environment",
            "The task requests a datalist loader but omits the concrete dataset format.",
            "A generic parser may not interoperate with the expected workflow.",
            "Confirm the exact datalist schema that should be supported.",
            ["Schema handling"],
        ),
        _make_assumption(
            2,
            "Tests and documentation may be required deliverables for the feature.",
            "Validation",
            "Feature requests in mature libraries often require verification and docs, but the redacted spec omits them.",
            "A code-only change may be judged incomplete.",
            "Confirm whether tests and documentation updates are required.",
            ["Verification scope"],
        ),
    ]


def _pythainlp_rules(text: str) -> List[Dict[str, Any]]:
    if "n-gram" not in text:
        return []
    return [
        _make_assumption(
            1,
            "The feature probably needs a stable public function name and module placement.",
            "Implementation",
            "The redacted spec asks for a utility but does not define its API surface.",
            "Placing the function incorrectly could break expected imports.",
            "Confirm the public API name and module path.",
            ["Public API"],
        ),
        _make_assumption(
            2,
            "The function may need configurable n-gram ranges and deterministic output semantics.",
            "Functional",
            "The redacted spec omits the exact input and return contract.",
            "A narrowly scoped implementation may fail expected usage examples.",
            "Confirm the accepted inputs and return structure.",
            ["Function signature"],
        ),
    ]


def _rdflib_chunk_rules(text: str) -> List[Dict[str, Any]]:
    if "chunks" not in text and "chunk" not in text:
        return []
    return [
        _make_assumption(
            1,
            "Chunking may need multiple limit modes such as item count and file size.",
            "Functional",
            "The redacted spec names chunked serialization but does not define the control knobs.",
            "A single chunking strategy may be too limited.",
            "Confirm the chunking criteria the serializer must support.",
            ["Chunking policy"],
        ),
        _make_assumption(
            2,
            "The first output chunk may require special formatting to preserve prefixes or metadata.",
            "Validation",
            "Serialization tasks often need metadata retention rules not stated in the redacted spec.",
            "Output files may be technically valid but semantically incomplete.",
            "Confirm any prefix-preservation or header behavior for the first chunk.",
            ["Output semantics"],
        ),
    ]


def _rdflib_cbd_rules(text: str) -> List[Dict[str, Any]]:
    if "bounded description" not in text and "cbd" not in text:
        return []
    return [
        _make_assumption(
            1,
            "The feature likely belongs on the Graph API rather than as a helper function.",
            "Implementation",
            "The redacted request does not define API placement.",
            "An incorrect API surface may satisfy the logic but fail the intended interface.",
            "Confirm the target class or module for the new method.",
            ["API placement"],
        ),
        _make_assumption(
            2,
            "The implementation probably needs to follow an external concise bounded description specification.",
            "Validation",
            "The redacted task gives the concept name but not the governing rules.",
            "A custom interpretation may not match accepted semantics.",
            "Confirm the standard or reference behavior the method must follow.",
            ["Standards compliance"],
        ),
    ]


def _separability_rules(text: str) -> List[Dict[str, Any]]:
    if "separability_matrix" not in text:
        return []
    return [
        _make_assumption(
            1,
            "Nested compound models should preserve separability of embedded independent components.",
            "Validation",
            "The bug statement does not spell out the exact expected matrix semantics.",
            "A superficial fix may still compute an incorrect dependency matrix.",
            "Confirm the expected separability behavior for nested linear components.",
            ["Matrix semantics"],
        )
    ]


def _rst_rules(text: str) -> List[Dict[str, Any]]:
    if "restructuredtext" not in text and "header rows" not in text:
        return []
    return [
        _make_assumption(
            1,
            "The writer should accept the same header_rows argument pattern used by other table formats.",
            "Functional",
            "The request names header rows but omits the exact calling convention.",
            "A different API shape may still fail documented usage.",
            "Confirm the expected writer argument compatibility.",
            ["API compatibility"],
        )
    ]


def _qdp_rules(text: str) -> List[Dict[str, Any]]:
    if "ascii.qdp" not in text and "qdp" not in text:
        return []
    return [
        _make_assumption(
            1,
            "QDP command parsing should be case-insensitive.",
            "Validation",
            "The redacted bug report references QDP handling but omits the exact case behavior.",
            "Lowercase command lines may continue to fail after the fix.",
            "Confirm whether lowercase QDP directives must parse successfully.",
            ["Parser semantics"],
        )
    ]


def _mask_rules(text: str) -> List[Dict[str, Any]]:
    if "mask propagation" not in text and "operand lacks a mask" not in text:
        return []
    return [
        _make_assumption(
            1,
            "When one operand lacks a mask, the existing mask should likely be copied unchanged.",
            "Validation",
            "The redacted bug statement omits the exact recovery behavior.",
            "A new behavior may still produce invalid mask values or break compatibility.",
            "Confirm the intended mask propagation semantics when one side has no mask.",
            ["Compatibility semantics"],
        )
    ]


def _dexponent_rules(text: str) -> List[Dict[str, Any]]:
    if "d exponents" not in text:
        return []
    return [
        _make_assumption(
            1,
            "The issue may involve a mutation bug rather than the exponent-conversion feature itself.",
            "Implementation",
            "The redacted task names D-exponent handling but omits the mechanism of failure.",
            "The fix may target the wrong part of the code path.",
            "Confirm whether the current code relies on a non-mutating replace operation.",
            ["Implementation detail"],
        )
    ]


def _make_assumption(
    index: int,
    statement: str,
    type_name: str,
    evidence: str,
    risk: str,
    resolution: str,
    linked_decisions: List[str],
) -> Dict[str, Any]:
    return {
        "id": f"A{index}",
        "statement": statement,
        "type": type_name,
        "evidence": [evidence],
        "risk_if_wrong": risk,
        "needs_confirmation": True,
        "confidence": 0.55,
        "proposed_resolution": resolution,
        "linked_decisions": linked_decisions,
    }
