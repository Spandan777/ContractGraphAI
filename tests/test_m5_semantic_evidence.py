from contractgraph.semantic_evidence import verify_semantic_support


def setup_data():
    by_id = {
        "C1": {"id": "C1", "text": "Customer shall pay within 30 days."},
        "C2": {"id": "C2", "text": "Invoices are payable within 60 days."},
    }
    finding = {
        "finding_id": "M4-payment-C1-C2",
        "risk_type": "payment_duration_mismatch",
        "claim": "The linked provisions state different payment periods.",
        "clauses": ["C1", "C2"],
        "evidence": [by_id["C1"]["text"], by_id["C2"]["text"]],
    }
    return by_id, finding


def test_disabled_semantic_assessment_makes_no_claim():
    by_id, finding = setup_data()
    result = verify_semantic_support([finding], by_id)[0]
    assert result["semantic_verdict"] == "insufficient_evidence"
    assert result["semantic_assessment_status"] == "disabled"
    assert result["semantic_assessed"] is False


def test_traceability_failure_blocks_semantic_assessment():
    by_id, finding = setup_data()
    finding["evidence"] = ["fabricated", by_id["C2"]["text"]]
    called = []
    result = verify_semantic_support(
        [finding], by_id, enabled=True,
        verifier=lambda f, c: called.append(True) or {},
    )[0]
    assert result["semantic_assessment_status"] == "blocked_unverified_evidence"
    assert not called


def test_supported_verdict_is_validated_and_preserved():
    by_id, finding = setup_data()
    verifier = lambda f, c: {
        "verdict": "supported", "rationale": "Both clauses state payment periods.",
        "confidence": 0.91, "supporting_clause_ids": ["C1", "C2"],
        "contradicting_clause_ids": [], "model": "test-model",
    }
    result = verify_semantic_support([finding], by_id, True, verifier)[0]
    assert result["semantic_verdict"] == "supported"
    assert result["semantic_assessed"] is True
    assert result["semantic_confidence"] == 0.91
    assert result["evidence"] == finding["evidence"]


def test_contradicted_and_insufficient_verdicts_are_supported():
    by_id, finding = setup_data()
    for verdict in ("contradicted", "insufficient_evidence"):
        verifier = lambda f, c, v=verdict: {
            "verdict": v, "rationale": "Conservative test assessment.",
            "confidence": 0.6, "supporting_clause_ids": [],
            "contradicting_clause_ids": ["C2"] if v == "contradicted" else [],
        }
        result = verify_semantic_support([finding], by_id, True, verifier)[0]
        assert result["semantic_verdict"] == verdict


def test_invalid_verdict_is_rejected_as_assessment_error():
    by_id, finding = setup_data()
    result = verify_semantic_support(
        [finding], by_id, True,
        lambda f, c: {"verdict": "legally_valid", "rationale": "x", "confidence": 0.8},
    )[0]
    assert result["semantic_assessment_status"] == "assessment_error"
    assert result["semantic_assessed"] is False


def test_out_of_scope_clause_ids_are_rejected():
    by_id, finding = setup_data()
    result = verify_semantic_support(
        [finding], by_id, True,
        lambda f, c: {"verdict": "supported", "rationale": "x", "confidence": 0.8,
                      "supporting_clause_ids": ["C999"], "contradicting_clause_ids": []},
    )[0]
    assert result["semantic_assessment_status"] == "assessment_error"


def test_pipeline_exposes_semantic_assessment_when_disabled():
    from contractgraph.pipeline import analyze_contract
    from contractgraph.sample_data import SAMPLE_CONTRACT
    result = analyze_contract(SAMPLE_CONTRACT)
    assert result["status"] == "success"
    assert result["semantic_verification_status"] == "disabled"
    assert "semantic_assessments" in result
    assert len(result["semantic_assessments"]) == len(result["verified_cross_clause_findings"])
