import json
from pathlib import Path
from src.contractgraph.annotation_schema import validate_record, validate_jsonl


def valid_record():
    return {
        "annotation_id": "ANN-1", "document_id": "DOC-1", "clause_a_id": "C1", "clause_b_id": "C2",
        "label": "risk", "risk_type": "payment_conflict", "severity": "medium",
        "rationale": "The clauses apply to the same invoice and set incompatible due dates.",
        "evidence_a": "Payment is due in 15 days.", "evidence_b": "Payment is due in 45 days.",
        "scope": "Both clauses govern invoices under the same services agreement.", "trigger": "Invoice issuance.",
        "exception": "None stated", "precedence": "None stated", "annotator": "reviewer-1", "review_status": "reviewed"
    }


def test_valid_annotation_record():
    assert validate_record(valid_record()) == []


def test_risk_requires_both_evidence_spans():
    row = valid_record()
    row["evidence_b"] = ""
    assert any("evidence_b is required" in e for e in validate_record(row))


def test_same_clause_pair_rejected():
    row = valid_record()
    row["clause_b_id"] = "C1"
    assert any("must be different" in e for e in validate_record(row))


def test_jsonl_duplicate_ids(tmp_path: Path):
    row = valid_record()
    p = tmp_path / "annotations.jsonl"
    p.write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n", encoding="utf-8")
    count, errors = validate_jsonl(p)
    assert count == 2
    assert any("duplicate annotation_id" in e for e in errors)
