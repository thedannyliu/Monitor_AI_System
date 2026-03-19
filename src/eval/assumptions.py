from __future__ import annotations

import re
from typing import Dict, List


def normalize_statement(text: str) -> str:
    lowered = text.lower()
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return lowered


def assumption_metrics(predicted: List[Dict[str, str]], gold: List[Dict[str, str]]) -> Dict[str, float]:
    matched_gold = set()
    true_positive = 0
    for pred in predicted:
        pred_text = normalize_statement(pred["statement"])
        match_index = _match_gold(pred_text, gold, matched_gold)
        if match_index is not None:
            matched_gold.add(match_index)
            true_positive += 1

    false_positive = max(len(predicted) - true_positive, 0)
    false_negative = max(len(gold) - true_positive, 0)
    precision = _safe_divide(true_positive, true_positive + false_positive)
    recall = _safe_divide(true_positive, true_positive + false_negative)
    f1 = _safe_divide(2 * precision * recall, precision + recall) if precision + recall else 0.0
    return {
        "tp": true_positive,
        "fp": false_positive,
        "fn": false_negative,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def _match_gold(pred_text: str, gold: List[Dict[str, str]], matched_gold: set) -> int | None:
    for index, gold_item in enumerate(gold):
        if index in matched_gold:
            continue
        gold_text = normalize_statement(gold_item["statement"])
        if pred_text == gold_text:
            return index
        if _token_overlap(pred_text, gold_text) >= 0.45:
            return index
    return None


def _token_overlap(left: str, right: str) -> float:
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    if not left_tokens or not right_tokens:
        return 0.0
    intersection = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)
    return intersection / union


def _safe_divide(num: float, denom: float) -> float:
    return num / denom if denom else 0.0
