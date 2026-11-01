"""Schema and validation helpers for human-reviewed cross-clause annotations."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VALID_LABELS = {"risk", "no_risk", "uncertain"}
VALID_RISK_TYPES = {
    "payment_conflict", "termination_conflict", "liability_conflict",
    "confidentiality_conflict", "obligation_conflict", "exception_interaction",
    "notice_requirement", "temporal_dependency", "other", "not_applicable",
}
VALID_SEVERITIES = {"low", "medium", "high", "not_applicable"}
VALID_REVIEW = {"draft", "reviewed", "adjudicated"}
REQUIRED = {
    "annotation_id", "document_id", "clause_a_id", "clause_b_id", "label",
    "risk_type", "severity", "rationale", "evidence_a", "evidence_b",
    "scope", "trigger", "exception", "precedence", "annotator", "review_status",
}


def validate_record(record: Any, line_number: int = 1) -> list[str]:
    errors: list[str] = []
    prefix = f"line {line_number}"
    if not isinstance(record, dict):
        return [f"{prefix}: record must be a JSON object"]
    missing = sorted(REQUIRED - record.keys())
    if missing:
        errors.append(f"{prefix}: missing fields: {', '.join(missing)}")
    for field in ("annotation_id", "document_id", "clause_a_id", "clause_b_id", "rationale", "annotator"):
        if field in record and (not isinstance(record[field], str) or not record[field].strip()):
            errors.append(f"{prefix}: {field} must be a non-empty string")
    if record.get("clause_a_id") == record.get("clause_b_id") and record.get("clause_a_id"):
        errors.append(f"{prefix}: clause_a_id and clause_b_id must be different")
    if record.get("label") not in VALID_LABELS:
        errors.append(f"{prefix}: label must be one of {sorted(VALID_LABELS)}")
    if record.get("risk_type") not in VALID_RISK_TYPES:
        errors.append(f"{prefix}: risk_type must be one of {sorted(VALID_RISK_TYPES)}")
    if record.get("severity") not in VALID_SEVERITIES:
        errors.append(f"{prefix}: severity must be one of {sorted(VALID_SEVERITIES)}")
    if record.get("review_status") not in VALID_REVIEW:
        errors.append(f"{prefix}: review_status must be one of {sorted(VALID_REVIEW)}")
    for field in ("evidence_a", "evidence_b"):
        if field in record and not isinstance(record[field], str):
            errors.append(f"{prefix}: {field} must be a string (use an empty string only when unavailable)")
    if record.get("label") == "risk":
        for field in ("evidence_a", "evidence_b"):
            if isinstance(record.get(field), str) and not record[field].strip():
                errors.append(f"{prefix}: {field} is required when label is risk")
        if record.get("risk_type") == "not_applicable":
            errors.append(f"{prefix}: risk records cannot use risk_type=not_applicable")
        if record.get("severity") == "not_applicable":
            errors.append(f"{prefix}: risk records cannot use severity=not_applicable")
    elif record.get("risk_type") not in (None, "not_applicable"):
        errors.append(f"{prefix}: non-risk records should use risk_type=not_applicable")
    return errors


def validate_jsonl(path: str | Path) -> tuple[int, list[str]]:
    path = Path(path)
    errors: list[str] = []
    count = 0
    if not path.exists():
        return 0, [f"File not found: {path}"]
    seen: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            try:
                record = json.loads(raw)
            except json.JSONDecodeError as exc:
                errors.append(f"line {line_number}: invalid JSON: {exc.msg}")
                continue
            count += 1
            errors.extend(validate_record(record, line_number))
            if isinstance(record, dict):
                annotation_id = record.get("annotation_id")
                if isinstance(annotation_id, str) and annotation_id in seen:
                    errors.append(f"line {line_number}: duplicate annotation_id: {annotation_id}")
                elif isinstance(annotation_id, str):
                    seen.add(annotation_id)
    return count, errors
