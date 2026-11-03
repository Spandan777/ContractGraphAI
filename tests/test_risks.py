from contractgraph.risks import detect_cross_clause_risks


def make_clause(clause_id, text):
    return {
        "id": clause_id,
        "text": text,
        "aspects": ["termination"],
    }


def test_renewal_exercise_notice_not_compared_with_termination_notice():
    clauses = [
        make_clause(
            "A",
            "Franchisee may renew for five years by giving written "
            "notice at least six months before the term expires."
        ),
        make_clause(
            "B",
            "The agreement may be terminated upon ninety days "
            "written notice."
        ),
    ]

    findings = detect_cross_clause_risks(clauses)

    assert not any(
        x["risk_type"] == "termination_duration_difference"
        for x in findings
    )


def test_renewal_exercise_notice_not_compared_with_nonrenewal_notice():
    clauses = [
        make_clause(
            "A",
            "Franchisee must give six months notice of its choice to renew."
        ),
        make_clause(
            "B",
            "The agreement requires 180 days notice of non-renewal."
        ),
    ]

    findings = detect_cross_clause_risks(clauses)

    assert not any(
        x["risk_type"] == "termination_duration_difference"
        for x in findings
    )


def test_different_termination_notice_periods_are_flagged():
    clauses = [
        make_clause(
            "A",
            "Either party may terminate this agreement upon thirty days "
            "prior written notice."
        ),
        make_clause(
            "B",
            "Either party may terminate this agreement upon ninety days "
            "prior written notice."
        ),
    ]

    findings = detect_cross_clause_risks(clauses)

    assert any(
        x["risk_type"] == "termination_duration_difference"
        for x in findings
    )


def test_cure_period_not_compared_with_termination_notice():
    clauses = [
        make_clause(
            "A",
            "A party may terminate after giving thirty days written notice."
        ),
        make_clause(
            "B",
            "The receiving party shall have sixty days to cure the breach."
        ),
    ]

    findings = detect_cross_clause_risks(clauses)

    assert not any(
        x["risk_type"] == "termination_duration_difference"
        for x in findings
    )


def test_liability_cap_difference_detection_is_preserved():
    clauses = [
        {
            "id": "A",
            "text": "Aggregate liability shall not exceed $100,000.",
            "aspects": ["liability"],
        },
        {
            "id": "B",
            "text": "Aggregate liability shall not exceed $500,000.",
            "aspects": ["liability"],
        },
    ]

    findings = detect_cross_clause_risks(clauses)

    assert any(
        x["risk_type"] == "liability_cap_difference"
        for x in findings
    )

def test_identical_clauses_with_multiple_durations_are_not_flagged():
    text = (
        "After the initial period of two years, the maintenance contract "
        "shall be automatically renewed for a period of one year on each "
        "renewal date."
    )

    clauses = [
        make_clause("A", text),
        make_clause("B", text),
    ]

    assert not duration_findings(clauses)


def test_initial_term_and_renewal_period_are_not_mismatched():
    clauses = [
        make_clause(
            "A",
            "The initial term is two years. Each renewal period is one year."
        ),
        make_clause(
            "B",
            "The initial term is two years. Each renewal period is one year."
        ),
    ]

    assert not duration_findings(clauses)


def test_identical_liability_caps_with_formatting_differences_are_not_flagged():
    clauses = [
        {
            "id": "A",
            "text": "Aggregate liability shall not exceed $100,000.",
            "aspects": ["liability"],
        },
        {
            "id": "B",
            "text": "AGGREGATE   LIABILITY shall not exceed $100,000.",
            "aspects": ["liability"],
        },
    ]

    findings = detect_cross_clause_risks(clauses)

    assert not any(
        x["risk_type"] == "liability_cap_difference"
        for x in findings
    )

def duration_findings(clauses):
    return [
        finding
        for finding in detect_cross_clause_risks(clauses)
        if finding["risk_type"] == "termination_duration_difference"
    ]
