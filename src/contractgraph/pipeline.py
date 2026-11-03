from datetime import datetime, timezone

from .ingestion import extract_text, validate_document
from .clauses import split_clauses
from .retrieval import retrieve
from .graph import build_dependency_graph, edges_as_dicts
from .risks import detect_cross_clause_risks
from .cross_clause_reasoning import detect_cross_clause_findings
from .evidence import verify_evidence
from .semantic_evidence import verify_semantic_support
from .gemini import analyze_with_gemini

QUERIES = {
    "payment": "payment invoice fees deadline",
    "termination": "termination expiry notice period",
    "liability": "liability indemnification damages limitation cap",
    "confidentiality": "confidential information disclosure duration",
}


def analyze_contract(source, use_gemini=False, verify_semantics=False):
    """Analyze a contract. Semantic assessment is opt-in and requires Gemini."""
    text = extract_text(source)
    validation = validate_document(text)
    if not validation["valid"]:
        return {
            "status": "invalid",
            "validation": validation,
            "clauses": [],
            "graph_edges": [],
            "baseline_retrieval": {},
            "verified_findings": [],
            "cross_clause_findings": [],
            "verified_cross_clause_findings": [],
            "semantic_assessments": [],
            "semantic_verification_status": "not_run_invalid_document",
        }

    clauses = split_clauses(text)
    by = {c["id"]: c for c in clauses}
    graph = build_dependency_graph(clauses)
    graph_edges = edges_as_dicts(graph)
    rules = detect_cross_clause_risks(clauses)
    cross_clause_findings = detect_cross_clause_findings(clauses, graph_edges, rules)
    gem = analyze_with_gemini(clauses) if use_gemini else {
        "status": "disabled", "findings": []
    }
    traceable_cross_clause_findings = verify_evidence(cross_clause_findings, by)
    semantic_assessments = verify_semantic_support(
        traceable_cross_clause_findings, by, enabled=verify_semantics
    )
    semantic_status = (
        "disabled" if not verify_semantics else
        "assessed" if any(x.get("semantic_assessed") for x in semantic_assessments) else
        "inconclusive_or_error"
    )

    return {
        "status": "success",
        "validation": validation,
        "clauses": clauses,
        "graph_nodes": list(graph.nodes(data=True)),
        "graph_edges": graph_edges,
        "baseline_retrieval": {
            key: retrieve(query, clauses, 3)
            for key, query in QUERIES.items()
        },
        "rule_findings": rules,
        "verified_findings": verify_evidence(rules, by),
        "cross_clause_findings": cross_clause_findings,
        "verified_cross_clause_findings": traceable_cross_clause_findings,
        "semantic_assessments": semantic_assessments,
        "semantic_verification_status": semantic_status,
        "gemini": {
            **gem,
            "verified_findings": verify_evidence(gem.get("findings", []), by),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
