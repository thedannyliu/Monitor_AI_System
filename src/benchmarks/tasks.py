from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from monitoring.schema import load_json


def load_manifest(path: str) -> List[Dict[str, Any]]:
    manifest_path = Path(path)
    payload = load_json(manifest_path)
    benchmark_name = payload.get("benchmark")
    tasks = []
    for item in payload["tasks"]:
        if isinstance(item, str):
            task_path = Path(item)
            if not task_path.is_absolute():
                repo_root = manifest_path.parents[3]
                task_path = repo_root / item
            task_payload = load_json(task_path)
        else:
            task_payload = item
        if benchmark_name and "benchmark" not in task_payload:
            task_payload["benchmark"] = benchmark_name
        tasks.append(task_payload)
    return tasks
