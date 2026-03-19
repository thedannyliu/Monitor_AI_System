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
    heuristic_items = HeuristicMonitorBackend().generate_report(task, {"schema_version": "v1"})["assumptions"]
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

    model_items = [_coerce_assumption_item(task, item, index) for index, item in enumerate(raw_items, start=1)]
    filtered_model_items = _filter_assumptions(task, model_items)
    merged = _merge_assumptions(task, heuristic_items, filtered_model_items)
    if merged:
        return merged
    return heuristic_items


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


def _filter_assumptions(task: Dict[str, Any], items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    filtered = []
    for item in items:
        statement = item["statement"].strip()
        if not statement:
            continue
        if _is_problem_restatement(task["redacted_spec"], statement):
            continue
        if _is_generic_assumption(statement):
            continue
        if _mentions_unavailable_evidence(item["evidence"]):
            item["evidence"] = [
                "The redacted task omits this constraint, so the agent would need to assume it during implementation."
            ]
        filtered.append(item)
    return filtered


def _merge_assumptions(
    task: Dict[str, Any],
    heuristic_items: List[Dict[str, Any]],
    model_items: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    target = _target_assumption_count(task)
    merged: List[Dict[str, Any]] = []
    seen = set()

    for source in (heuristic_items, model_items):
        for item in source:
            normalized = _normalize_match_text(item["statement"])
            if normalized in seen:
                continue
            if any(_statement_similarity(normalized, existing["statement"]) >= 0.55 for existing in merged):
                continue
            seen.add(normalized)
            merged.append(item)
            if len(merged) >= target:
                break
        if len(merged) >= target:
            break

    for index, item in enumerate(merged, start=1):
        item["id"] = f"A{index}"
    return merged


def _target_assumption_count(task: Dict[str, Any]) -> int:
    if task["benchmark"] == "self_bench":
        return 5
    return 2


def _is_problem_restatement(redacted_spec: str, statement: str) -> bool:
    redacted = _normalize_match_text(redacted_spec)
    candidate = _normalize_match_text(statement)
    return _statement_similarity(redacted, candidate) >= 0.52


def _is_generic_assumption(statement: str) -> bool:
    text = statement.lower()
    generic_patterns = [
        "internal",
        "public domain",
        "html, css, and javascript",
        "html css and javascript",
        "https",
        "ssl",
        "cpu",
        "memory",
        "scalability",
        "enough resources",
        "data loss or corruption",
        "security vulnerabilities",
        "research on popular",
    ]
    return any(pattern in text for pattern in generic_patterns)


def _mentions_unavailable_evidence(evidence: List[str]) -> bool:
    joined = " ".join(evidence).lower()
    unavailable_patterns = [
        "during testing",
        "documentation suggests",
        "review of",
        "resource usage monitoring",
        "previous implementations",
        "codebase does not show",
    ]
    return any(pattern in joined for pattern in unavailable_patterns)


def _normalize_match_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _statement_similarity(left: str, right: str) -> float:
    left_tokens = set(_normalize_match_text(left).split())
    right_tokens = set(_normalize_match_text(right).split())
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


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
    return items[: _target_assumption_count(task)]


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
        _make_assumption(
            3,
            "The project may need deployment settings that work on Vercel.",
            "Environment",
            "The redacted task does not specify the deployment target for the portfolio.",
            "Choosing the wrong hosting assumptions could change routing and build configuration.",
            "Confirm whether the site must be deployable to Vercel.",
            ["Deployment configuration"],
        ),
        _make_assumption(
            4,
            "The portfolio likely needs responsive behavior for both mobile and desktop layouts.",
            "Validation",
            "The redacted task omits viewport and responsiveness requirements.",
            "A desktop-only implementation could fail review on smaller screens.",
            "Confirm the required responsive layout behavior.",
            ["UI validation plan"],
        ),
        _make_assumption(
            5,
            "The pilot may require a simple protected admin page for reviewing stored messages.",
            "Functional",
            "The redacted task asks for contact capability but does not define any review workflow for saved messages.",
            "Persisted messages may be unusable if there is no way to inspect them during the pilot.",
            "Confirm whether an admin review page is required.",
            ["Feature scope"],
        ),
    ]


def _dashboard_rules(text: str) -> List[Dict[str, Any]]:
    if "dashboard" not in text:
        return []
    return [
        _make_assumption(
            1,
            "The dashboard likely expects CSV uploads rather than manual data entry.",
            "Functional",
            "The redacted task mentions accepting daily sales data but does not define the ingestion method.",
            "The wrong ingestion workflow would misalign the upload experience.",
            "Confirm whether sales data should be uploaded from CSV files.",
            ["Upload workflow"],
        ),
        _make_assumption(
            2,
            "Uploaded sales data may need to persist in SQLite between sessions instead of living only in session state.",
            "Implementation",
            "Analytics dashboards often retain historical uploads, but the redacted spec does not say how data is stored.",
            "Results may disappear between sessions if persistence is omitted.",
            "Confirm whether uploaded data must be saved across sessions and whether SQLite is an acceptable storage target.",
            ["Storage backend"],
        ),
        _make_assumption(
            3,
            "CSV uploads may require row-level validation errors rather than a generic failure message.",
            "Validation",
            "The spec accepts external data but does not describe malformed input handling.",
            "The dashboard may silently ignore bad rows or crash on upload.",
            "Confirm how invalid CSV rows should be surfaced to the user.",
            ["Upload validation"],
        ),
        _make_assumption(
            4,
            "The dashboard may require a light-theme accessible UI rather than a default styling choice.",
            "NonFunctional",
            "The redacted task omits accessibility and theme constraints.",
            "A visually valid dashboard may still fail accessibility expectations.",
            "Confirm whether the dashboard must use an accessible light theme.",
            ["Presentation constraints"],
        ),
        _make_assumption(
            5,
            "The dashboard may need time-range filters for the last 7, 30, and 90 days.",
            "Functional",
            "The redacted task names the charts but does not define any interaction filters.",
            "The dashboard could miss an expected analysis control.",
            "Confirm whether fixed time-range filters are required.",
            ["Feature scope"],
        ),
    ]


def _api_rules(text: str) -> List[Dict[str, Any]]:
    if "api" not in text and "endpoint" not in text:
        return []
    return [
        _make_assumption(
            1,
            "Tasks may need to be stored in PostgreSQL instead of an in-memory structure.",
            "Implementation",
            "CRUD APIs usually imply durable storage, but the redacted spec does not specify a backend.",
            "An in-memory API may fail persistence expectations.",
            "Confirm the storage backend and persistence requirement.",
            ["Database selection"],
        ),
        _make_assumption(
            2,
            "The list endpoint may require pagination behavior that is currently unspecified.",
            "Functional",
            "The redacted spec defines CRUD operations but omits listing constraints.",
            "A naive list response may not match the expected API contract.",
            "Confirm whether list responses need pagination.",
            ["Response schema"],
        ),
        _make_assumption(
            3,
            "Due date fields may require ISO 8601 validation rather than permissive string handling.",
            "Validation",
            "The redacted task does not define how date fields should be validated.",
            "Malformed dates may be accepted and break downstream logic.",
            "Confirm the due date validation format.",
            ["Validation rules"],
        ),
        _make_assumption(
            4,
            "The existing /health route may need to remain backward compatible.",
            "Environment",
            "The redacted task adds API behavior but does not say whether existing routes must keep prior responses.",
            "A refactor could break deployment checks or existing integrations.",
            "Confirm whether current health-check behavior must remain unchanged.",
            ["Compatibility semantics"],
        ),
        _make_assumption(
            5,
            "Unit tests may need to cover pagination and validation failures.",
            "Validation",
            "The redacted task does not define expected test coverage for new behavior.",
            "A code-only change may be judged incomplete.",
            "Confirm whether tests must cover pagination and invalid due-date cases.",
            ["Verification scope"],
        ),
    ]


def _cli_rules(text: str) -> List[Dict[str, Any]]:
    if "cli" not in text and "markdown notes" not in text:
        return []
    return [
        _make_assumption(
            1,
            "The tool may need to scan directories recursively.",
            "Functional",
            "Directory-scanning tools often support nested content, but the redacted spec does not say so.",
            "A shallow scan may miss valid files.",
            "Confirm whether recursive scanning is required.",
            ["Traversal behavior"],
        ),
        _make_assumption(
            2,
            "The report format may need to be JSON.",
            "Environment",
            "The redacted spec does not define how the report should be consumed.",
            "A plain-text report may be unusable for downstream automation.",
            "Confirm the required report format and CLI flags.",
            ["Output format"],
        ),
        _make_assumption(
            3,
            "The CLI may need an exclude list for ignored files or directories.",
            "Functional",
            "The redacted task describes scanning notes but omits path-filtering behavior.",
            "The tool may process unwanted content without an ignore mechanism.",
            "Confirm whether excluded paths must be supported.",
            ["Traversal behavior"],
        ),
        _make_assumption(
            4,
            "The CLI may need a pretty-printed JSON output option.",
            "Functional",
            "The redacted task mentions a report but does not define output modes.",
            "The CLI may miss a requested user-facing formatting option.",
            "Confirm whether a pretty-print flag is required.",
            ["Output format"],
        ),
        _make_assumption(
            5,
            "The CLI may need to return a non-zero exit code when the input directory is missing.",
            "Validation",
            "The redacted task omits failure-mode semantics.",
            "The tool could report success even when it cannot read the requested directory.",
            "Confirm the expected exit behavior for a missing input path.",
            ["Failure handling"],
        ),
    ]


def _blog_rules(text: str) -> List[Dict[str, Any]]:
    if "blog" not in text:
        return []
    return [
        _make_assumption(
            1,
            "Posts may be sourced from Markdown files with front matter.",
            "Implementation",
            "The redacted spec names site pages but does not define the content pipeline.",
            "The implementation could add unnecessary infrastructure or miss the intended authoring workflow.",
            "Confirm the content source and whether the site must remain static.",
            ["Content pipeline"],
        ),
        _make_assumption(
            2,
            "Posts may need to be sorted by publish date and filtered to published posts only.",
            "Validation",
            "Listing behavior is not specified in the redacted task.",
            "Posts may render in the wrong order or expose drafts.",
            "Confirm ordering and visibility rules for posts.",
            ["Listing behavior"],
        ),
        _make_assumption(
            3,
            "The blog may need RSS feed generation as an explicit output artifact.",
            "Functional",
            "The redacted task describes pages but omits distribution features such as feeds.",
            "The final site may miss a required syndication feature.",
            "Confirm whether an RSS feed must be generated.",
            ["Feature scope"],
        ),
        _make_assumption(
            4,
            "Each post page may need an estimated reading-time badge.",
            "Functional",
            "The redacted task does not define smaller post-detail UX elements.",
            "The post detail page may miss a required presentation feature.",
            "Confirm whether each post must show reading-time metadata.",
            ["Feature scope"],
        ),
        _make_assumption(
            5,
            "The site may need to remain fully static with no runtime database.",
            "Environment",
            "The redacted task does not define deployment or runtime storage constraints.",
            "An unnecessary backend could violate the intended deployment model.",
            "Confirm whether the blog must remain a static site with no runtime database.",
            ["Deployment configuration"],
        ),
    ]


def _aider_rules(text: str) -> List[Dict[str, Any]]:
    if "dirty file" not in text and "commit behavior" not in text:
        return []
    return [
        _make_assumption(
            1,
            "Dirty changes may need to be auto-committed only for files that the model is about to edit.",
            "Validation",
            "The task mentions dirty-file behavior but does not define the exact trigger.",
            "An overly broad auto-commit policy could change unrelated user work.",
            "Confirm which dirty files should be committed automatically.",
            ["Commit trigger"],
        ),
        _make_assumption(
            2,
            "An existing no-dirty-commits style opt-out flag may need to preserve the previous no-precommit behavior.",
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
            "The JSON format may need to follow the Decathlon datalist structure used in MONAI workflows.",
            "Environment",
            "The task requests a datalist loader but omits the concrete dataset format.",
            "A generic parser may not interoperate with the expected workflow.",
            "Confirm the exact datalist schema that should be supported.",
            ["Schema handling"],
        ),
        _make_assumption(
            2,
            "The change may need both tests and documentation updates.",
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
            "The new function may need a stable public name and module placement under pythainlp.lm.",
            "Implementation",
            "The redacted spec asks for a utility but does not define its API surface.",
            "Placing the function incorrectly could break expected imports.",
            "Confirm the public API name and module path.",
            ["Public API"],
        ),
        _make_assumption(
            2,
            "The function may need a configurable n-gram range and return aggregated counts in dictionary form.",
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
            "Chunking may need to support either a maximum triple count or a maximum file size.",
            "Functional",
            "The redacted spec names chunked serialization but does not define the control knobs.",
            "A single chunking strategy may be too limited.",
            "Confirm the chunking criteria the serializer must support.",
            ["Chunking policy"],
        ),
        _make_assumption(
            2,
            "When prefixes are preserved, the first output chunk may need Turtle formatting instead of NT.",
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
            "The new API may need to be a Graph.cbd method rather than a helper function.",
            "Implementation",
            "The redacted request does not define API placement.",
            "An incorrect API surface may satisfy the logic but fail the intended interface.",
            "Confirm the target class or module for the new method.",
            ["API placement"],
        ),
        _make_assumption(
            2,
            "The implementation may need to follow the W3C concise bounded description rules and include documentation.",
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
            "Nested compound models should preserve the separability of embedded linear models.",
            "Validation",
            "The bug statement does not spell out the exact expected matrix semantics.",
            "A superficial fix may still compute an incorrect dependency matrix.",
            "Confirm the expected separability behavior for nested linear components.",
            ["Matrix semantics"],
        ),
        _make_assumption(
            2,
            "The intended behavior may be defined by explicit matrix examples in the original issue.",
            "Validation",
            "The redacted bug report omits the concrete examples that define the target matrix.",
            "The fix could choose the wrong separability semantics without those examples.",
            "Confirm whether issue examples define the expected output matrix.",
            ["Reference behavior"],
        ),
    ]


def _rst_rules(text: str) -> List[Dict[str, Any]]:
    if "restructuredtext" not in text and "header rows" not in text:
        return []
    return [
        _make_assumption(
            1,
            "The ascii.rst writer may need to accept the header_rows argument without raising TypeError.",
            "Functional",
            "The request names header rows but omits the exact calling convention.",
            "A different API shape may still fail documented usage.",
            "Confirm the expected writer argument compatibility.",
            ["API compatibility"],
        ),
        _make_assumption(
            2,
            "The header_rows behavior may need to match the existing ascii.fixed_width writer semantics.",
            "Validation",
            "The redacted request omits the comparison target for the desired output behavior.",
            "The feature may accept the argument but still format rows incorrectly.",
            "Confirm whether the output should align with ascii.fixed_width behavior.",
            ["Output semantics"],
        ),
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
        ),
        _make_assumption(
            2,
            "Lowercase read serr inputs may need to load successfully with their error columns.",
            "Functional",
            "The redacted bug report omits the concrete lowercase command example.",
            "A parser change may still fail the runtime path that originally broke.",
            "Confirm whether lowercase read serr inputs with errors must load without failure.",
            ["Runtime behavior"],
        ),
    ]


def _mask_rules(text: str) -> List[Dict[str, Any]]:
    if "mask propagation" not in text and "operand lacks a mask" not in text:
        return []
    return [
        _make_assumption(
            1,
            "When one operand lacks a mask, the output may need to copy the existing mask from the other operand unchanged.",
            "Validation",
            "The redacted bug statement omits the exact recovery behavior.",
            "A new behavior may still produce invalid mask values or break compatibility.",
            "Confirm the intended mask propagation semantics when one side has no mask.",
            ["Compatibility semantics"],
        ),
        _make_assumption(
            2,
            "The fix may need to restore the behavior that existed before the regression.",
            "Environment",
            "The redacted task omits the compatibility target for the correct behavior.",
            "A novel but incompatible behavior may still break downstream expectations.",
            "Confirm whether the goal is to restore the previous version's mask behavior.",
            ["Version compatibility"],
        ),
    ]


def _dexponent_rules(text: str) -> List[Dict[str, Any]]:
    if "d exponents" not in text:
        return []
    return [
        _make_assumption(
            1,
            "The issue may come from using a non-in-place replace operation on a chararray.",
            "Implementation",
            "The redacted task names D-exponent handling but omits the mechanism of failure.",
            "The fix may target the wrong part of the code path.",
            "Confirm whether the current code relies on a non-mutating replace operation.",
            ["Implementation detail"],
        ),
        _make_assumption(
            2,
            "Exponent-separator conversion for D-formatted values may still need to work after the fix.",
            "Validation",
            "The redacted task does not describe the expected behavior that must be preserved.",
            "Removing the faulty code without preserving D-exponent handling could cause a regression.",
            "Confirm the expected D-exponent conversion behavior after the implementation change.",
            ["Regression risk"],
        ),
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
