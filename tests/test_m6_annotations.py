\
from contractgraph.m6_annotations import validate_annotation, cohen_kappa


def row():
    return {
        "candidate_id":"P1", "document_id":"D1", "evidence_span_a_id":"S1", "evidence_span_b_id":"S2",
        "evidence_a":"Text A", "evidence_b":"Text B", "paragraph_context_a":"Context A", "paragraph_context_b":"Context B",
        "label":"risk", "risk_type":"payment_conflict", "severity":"medium", "rationale":"Incompatible due dates.",
        "scope_analysis":"Same invoices", "trigger_analysis":"Invoice receipt", "exception_analysis":"None",
        "precedence_analysis":"No precedence", "annotator":"reviewer1", "review_status":"reviewed"
    }


def test_valid_human_annotation():
    assert validate_annotation(row()) == []


def test_pending_record_not_valid_gold():
    r=row(); r["review_status"]="pending_human_review"
    assert any("pending human review" in x for x in validate_annotation(r))


def test_risk_requires_both_evidence_spans():
    r=row(); r["evidence_b"]=""
    assert any("requires both evidence" in x for x in validate_annotation(r))


def test_kappa_perfect_agreement():
    r=cohen_kappa(["risk","no_risk","risk"],["risk","no_risk","risk"])
    assert r["observed_agreement"] == 1.0 and r["cohen_kappa"] == 1.0


def test_kappa_disagreement():
    r=cohen_kappa(["risk","risk","no_risk","no_risk"],["risk","no_risk","risk","no_risk"])
    assert r["observed_agreement"] == 0.5 and r["cohen_kappa"] == 0.0
