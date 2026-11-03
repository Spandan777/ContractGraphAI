from __future__ import annotations
import json
from pathlib import Path
from collections import Counter

LABELS = {"risk", "no_risk", "uncertain"}
RISK_TYPES = {
    "payment_conflict", "termination_conflict", "liability_conflict",
    "confidentiality_conflict", "obligation_conflict", "exception_interaction",
    "notice_requirement", "temporal_dependency", "other", "not_applicable",
}
SEVERITIES = {"low", "medium", "high", "not_applicable"}
REVIEW_STATES = {"pending_human_review", "reviewed", "adjudicated"}
REQUIRED = {
    "candidate_id", "document_id", "evidence_span_a_id", "evidence_span_b_id",
    "evidence_a", "evidence_b", "paragraph_context_a", "paragraph_context_b",
    "label", "risk_type", "severity", "rationale", "scope_analysis",
    "trigger_analysis", "exception_analysis", "precedence_analysis",
    "annotator", "review_status",
}


def read_jsonl(path):
    rows = []
    with Path(path).open("r", encoding="utf-8-sig") as f:
        for n, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{n}: invalid JSON: {exc.msg}") from exc
    return rows


def write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def validate_annotation(row, index=1, gold_only=False):
    errors = []
    prefix = f"record {index}"
    missing = sorted(REQUIRED - set(row))
    if missing:
        errors.append(f"{prefix}: missing fields: {', '.join(missing)}")
        return errors
    for key in ("candidate_id", "document_id", "evidence_span_a_id", "evidence_span_b_id", "annotator"):
        if not isinstance(row.get(key), str) or not row[key].strip():
            errors.append(f"{prefix}: {key} must be a non-empty string")
    if row.get("evidence_span_a_id") == row.get("evidence_span_b_id"):
        errors.append(f"{prefix}: evidence span IDs must differ")
    if row.get("label") not in LABELS:
        errors.append(f"{prefix}: label must be one of {sorted(LABELS)}")
    if row.get("risk_type") not in RISK_TYPES:
        errors.append(f"{prefix}: invalid risk_type")
    if row.get("severity") not in SEVERITIES:
        errors.append(f"{prefix}: invalid severity")
    if row.get("review_status") not in REVIEW_STATES:
        errors.append(f"{prefix}: invalid review_status")
    for key in ("evidence_a", "evidence_b", "paragraph_context_a", "paragraph_context_b",
                "rationale", "scope_analysis", "trigger_analysis", "exception_analysis",
                "precedence_analysis"):
        if not isinstance(row.get(key), str):
            errors.append(f"{prefix}: {key} must be a string")
    if row.get("label") == "risk":
        if not row.get("evidence_a", "").strip() or not row.get("evidence_b", "").strip():
            errors.append(f"{prefix}: risk requires both evidence spans")
        if row.get("risk_type") == "not_applicable" or row.get("severity") == "not_applicable":
            errors.append(f"{prefix}: risk requires risk_type and severity")
    elif row.get("risk_type") != "not_applicable" or row.get("severity") != "not_applicable":
        errors.append(f"{prefix}: no_risk/uncertain must use not_applicable risk_type and severity")
    if row.get("review_status") == "pending_human_review":
        errors.append(f"{prefix}: annotation is still pending human review")
    if not row.get("rationale", "").strip():
        errors.append(f"{prefix}: rationale is required")
    if gold_only and row.get("review_status") != "adjudicated":
        errors.append(f"{prefix}: gold benchmark records must be adjudicated")
    return errors


def validate_annotation_file(path, gold_only=False):
    rows = read_jsonl(path)
    errors, seen = [], set()
    for i, row in enumerate(rows, 1):
        errors.extend(validate_annotation(row, i, gold_only=gold_only))
        cid = row.get("candidate_id") if isinstance(row, dict) else None
        if cid in seen:
            errors.append(f"record {i}: duplicate candidate_id {cid}")
        elif cid:
            seen.add(cid)
    return rows, errors


def cohen_kappa(labels_a, labels_b):
    if len(labels_a) != len(labels_b):
        raise ValueError("Annotator label arrays must have equal length")
    n = len(labels_a)
    if n == 0:
        raise ValueError("No overlapping annotations")
    categories = sorted(set(labels_a) | set(labels_b))
    observed = sum(a == b for a, b in zip(labels_a, labels_b)) / n
    counts_a, counts_b = Counter(labels_a), Counter(labels_b)
    expected = sum((counts_a[c] / n) * (counts_b[c] / n) for c in categories)
    kappa = (observed - expected) / (1 - expected) if expected < 1 else (1.0 if observed == 1 else 0.0)
    matrix = {a: {b: sum(x == a and y == b for x, y in zip(labels_a, labels_b)) for b in categories} for a in categories}
    return {"n": n, "categories": categories, "observed_agreement": observed,
            "expected_agreement": expected, "cohen_kappa": kappa, "confusion_matrix": matrix}


def agreement_from_files(path_a, path_b):
    a_rows, b_rows = read_jsonl(path_a), read_jsonl(path_b)
    def index(rows, label):
        out = {}
        for r in rows:
            cid = r.get("candidate_id")
            if cid in out:
                raise ValueError(f"Duplicate candidate_id {cid} in {label}")
            if r.get("label") not in LABELS:
                raise ValueError(f"Unlabelled or invalid record {cid} in {label}")
            out[cid] = r["label"]
        return out
    aa, bb = index(a_rows, "annotator A"), index(b_rows, "annotator B")
    shared = sorted(set(aa) & set(bb))
    if not shared:
        raise ValueError("No shared candidate IDs between annotators")
    result = cohen_kappa([aa[x] for x in shared], [bb[x] for x in shared])
    result["shared_candidate_ids"] = shared
    result["only_in_a"] = sorted(set(aa) - set(bb))
    result["only_in_b"] = sorted(set(bb) - set(aa))
    return result
