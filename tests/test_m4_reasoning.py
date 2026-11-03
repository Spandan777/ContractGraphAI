from contractgraph.cross_clause_reasoning import detect_cross_clause_findings


def clauses():
    return [
        {"id": "C1", "index": 1, "title": "Payment 1",
         "text": "Customer shall pay invoices within thirty (30) days after receipt.",
         "aspects": ["payment", "obligation"]},
        {"id": "C2", "index": 2, "title": "Payment 2",
         "text": "Invoices shall be payable within sixty (60) days after approval.",
         "aspects": ["payment", "obligation"]},
        {"id": "C3", "index": 3, "title": "Confidentiality exception",
         "text": "Confidential information may be disclosed under the exception in Section 8, except where prohibited by law.",
         "aspects": ["confidentiality", "exception"]},
        {"id": "C4", "index": 4, "title": "Confidentiality survival",
         "text": "Confidentiality obligations survive for five years after termination.",
         "aspects": ["confidentiality", "termination"]},
    ]


def edges():
    return [
        {"source": "C1", "target": "C2", "relation": "potential_conflict"},
        {"source": "C3", "target": "C4", "relation": "explicit_reference"},
        {"source": "C3", "target": "C4", "relation": "shared_aspect"},
    ]


def test_payment_period_mismatch_is_generated_with_exact_evidence():
    results = detect_cross_clause_findings(clauses(), edges())
    finding = next(x for x in results if x["risk_type"] == "payment_duration_mismatch")
    assert finding["clauses"] == ["C1", "C2"]
    assert len(finding["evidence"]) == 2
    assert "thirty" in finding["evidence"][0]
    assert "sixty" in finding["evidence"][1]
    assert finding["semantic_conflict_confirmed"] is False


def test_exception_and_survival_review_candidates_are_generated():
    results = detect_cross_clause_findings(clauses(), edges())
    types = {x["risk_type"] for x in results}
    assert "exception_scope_review" in types
    assert "survival_scope_review" in types


def test_unconnected_pairs_are_not_considered():
    results = detect_cross_clause_findings(clauses(), [])
    assert results == []


def test_existing_rule_findings_are_preserved():
    existing = [{
        "risk_type": "payment_duration_difference",
        "severity": "medium", "clauses": ["C1", "C2"],
        "claim": "Different payment periods.", "rationale": "Review scope.",
    }]
    results = detect_cross_clause_findings(clauses(), edges(), existing)
    assert any(x["risk_type"] == "payment_duration_difference" for x in results)


def test_all_findings_are_traceable_and_reviewable():
    results = detect_cross_clause_findings(clauses(), edges())
    assert results
    for finding in results:
        assert finding["finding_status"] == "candidate_for_human_review"
        assert len(finding["clauses"]) == len(finding["evidence"])
        assert finding["reasoning_method"]
        assert finding["graph_relations"]
        assert 0 <= finding["confidence"] <= 1


def test_same_clause_pairs_are_never_created():
    results = detect_cross_clause_findings(
        clauses(), [{"source": "C1", "target": "C1", "relation": "potential_conflict"}]
    )
    assert results == []


def test_pipeline_exposes_cross_clause_findings():
    from contractgraph.pipeline import analyze_contract
    from contractgraph.sample_data import SAMPLE_CONTRACT

    result = analyze_contract(SAMPLE_CONTRACT)
    assert result["status"] == "success"
    assert "cross_clause_findings" in result
    assert "verified_cross_clause_findings" in result
    for finding in result["cross_clause_findings"]:
        assert finding["finding_status"] == "candidate_for_human_review"

def test_initial_term_and_renewal_period_are_classified_separately():
    from contractgraph.cross_clause_reasoning import _duration_values

    text = (
        "The initial term is two years. "
        "The contract renews for a period of one year."
    )

    values = _duration_values(text, "termination")

    assert values[0][3] == "initial_term"
    assert values[1][3] == "renewal_period"


def test_different_initial_terms_are_not_confused_with_renewal_periods():
    from contractgraph.cross_clause_reasoning import _duration_values

    text = (
        "The initial term is three years. "
        "The contract renews for a period of one year."
    )

    values = _duration_values(text, "termination")

    assert values[0][3] == "initial_term"
    assert values[1][3] == "renewal_period"


def test_equal_initial_and_renewal_durations_keep_distinct_roles():
    from contractgraph.cross_clause_reasoning import _duration_values

    text = (
        "The initial term is two years. "
        "The contract renews for a period of two years."
    )

    values = _duration_values(text, "termination")

    assert values[0][3] == "initial_term"
    assert values[1][3] == "renewal_period"


def test_slovak_wireless_duration_roles_are_classified_correctly():
    from contractgraph.cross_clause_reasoning import _duration_values

    text = (
        "After the initial period of two years, the maintenance "
        "and support contract shall be automatically renewed "
        "for a period of one year on each renewal date, unless "
        "one of the parties terminates the contract through "
        "written notification at least six weeks prior to the "
        "renewal date."
    )

    values = _duration_values(text, "termination")

    assert values[0][3] == "initial_term"
    assert values[1][3] == "renewal_period"
    assert values[2][3] == "renewal_notice"

def test_a5_merges_equivalent_liability_cap_findings():
    liability_clauses = [
        {
            "id": "L1", "index": 1, "title": "Provider liability",
            "text": "Provider aggregate liability is capped at $1,000,000.",
            "aspects": ["liability"],
        },
        {
            "id": "L2", "index": 2, "title": "Customer liability",
            "text": "Customer aggregate liability is capped at $500,000.",
            "aspects": ["liability"],
        },
    ]
    liability_edges = [
        {"source": "L1", "target": "L2", "relation": "potential_conflict"},
    ]
    a2_findings = [{
        "risk_type": "liability_cap_difference",
        "severity": "high",
        "clauses": ["L1", "L2"],
        "claim": "Different liability cap expressions appear.",
        "rationale": "Review whether the caps govern different claim types.",
    }]

    results = detect_cross_clause_findings(
        liability_clauses, liability_edges, a2_findings
    )

    liability_results = [
        item for item in results
        if item["risk_type"] in {
            "liability_cap_scope_review",
            "liability_cap_difference",
        }
    ]

    assert len(liability_results) == 1
    assert liability_results[0]["risk_type"] == "liability_cap_scope_review"
    assert (
        liability_results[0]["signals"]["existing_rule_finding"]["risk_type"]
        == "liability_cap_difference"
    )
