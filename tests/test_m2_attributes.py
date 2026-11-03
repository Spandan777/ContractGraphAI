from contractgraph.attribute_extraction import extract_clause_attributes
from contractgraph.clauses import split_clauses


def test_attribute_extraction_duration_money_exception_and_reference():
    text = (
        "The Customer shall pay USD 12,500 within thirty (30) days after receipt. "
        "Except for fraud, liability shall not exceed USD 50,000. "
        "This obligation survives for five years under Section 4.2."
    )
    result = extract_clause_attributes(text)
    assert any(x["value"] == 30 for x in result["durations"])
    assert any(x["amount"] == "12500" for x in result["monetary_values"])
    assert result["has_exception"]
    assert "4.2" in result["references"]
    assert result["has_survival_language"]


def test_clause_segmentation_keeps_existing_fields_and_adds_attributes():
    clauses = split_clauses(
        "1. Payment\nThe Customer shall pay within thirty days.\n\n"
        "2. Termination\nEither party may terminate on fifteen days notice."
    )
    assert clauses
    assert all("aspects" in c and "durations" in c for c in clauses)
    assert all("obligations" in c and "exceptions" in c for c in clauses)
