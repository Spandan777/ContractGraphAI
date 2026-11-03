import sys
import json
import csv
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from contractgraph.retrieval import retrieve
from contractgraph.risks import detect_cross_clause_risks
from contractgraph.graph import build_dependency_graph, edges_as_dicts
from contractgraph.cross_clause_reasoning import detect_cross_clause_findings
from contractgraph.evidence import verify_evidence

SOURCE = ROOT / "data" / "processed" / "m7_real_contract_pairs.jsonl"
OUT = ROOT / "results" / "m7_real_contract_exploration_a5_merge_fix"

ASPECTS = {
    "Cap On Liability": ["liability"],
    "Uncapped Liability": ["liability"],
    "Termination For Convenience": ["termination"],
    "Post-Termination Services": ["termination"],
    "Revenue/Profit Sharing": ["payment"],
    "Renewal Term": ["termination"],
    "Notice Period To Terminate Renewal": ["termination"],
}

QUERIES = {
    "liability": "liability cap uncapped damages limitation",
    "termination": "termination notice post termination services",
    "payment_termination": "payment revenue sharing termination services",
    "renewal_termination": "renewal term termination notice period",
}

def load_pairs():
    with SOURCE.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

def make_clauses(row):
    return [
        {
            "id": "PAIR_A",
            "title": row["category_a"],
            "text": row["clause_a"],
            "aspects": ASPECTS.get(row["category_a"], []),
            "index": 1,
        },
        {
            "id": "PAIR_B",
            "title": row["category_b"],
            "text": row["clause_b"],
            "aspects": ASPECTS.get(row["category_b"], []),
            "index": 2,
        },
    ]

def main():
    pairs = load_pairs()
    OUT.mkdir(parents=True, exist_ok=True)

    results = []
    details_path = OUT / "pair_findings.jsonl"
    errors = []

    with details_path.open("w", encoding="utf-8") as detail_file:
        for index, row in enumerate(pairs, 1):
            try:
                clauses = make_clauses(row)
                by_id = {c["id"]: c for c in clauses}

                # Retrieval diagnostic, not a risk prediction.
                query = QUERIES.get(row["relation"], row["relation"])
                retrieved = retrieve(query, clauses, k=2)

                # A2: existing deterministic pairwise rules.
                a2_findings = detect_cross_clause_risks(clauses)

                # Build graph.
                graph = build_dependency_graph(clauses)
                edges = edges_as_dicts(graph)

                # A4: graph reasoning without injected A2 findings.
                a4_findings = detect_cross_clause_findings(
                    clauses,
                    edges,
                    existing_findings=None,
                )

                # A5: combined rule and graph findings.
                a5_findings = detect_cross_clause_findings(
                    clauses,
                    edges,
                    existing_findings=a2_findings,
                )

                a2_verified = verify_evidence(a2_findings, by_id)
                a4_verified = verify_evidence(a4_findings, by_id)
                a5_verified = verify_evidence(a5_findings, by_id)

                result = {
                    "pair_id": row["pair_id"],
                    "document_id": row["document_id"],
                    "relation": row["relation"],
                    "label": "unlabeled",
                    "retrieved_count": len(retrieved),
                    "A2_rule_candidates": len(a2_findings),
                    "A4_graph_candidates": len(a4_findings),
                    "A5_hybrid_candidates": len(a5_findings),
                    "graph_edges": len(edges),
                    "A2_traceable": sum(
                        bool(x.get("evidence_verified")) for x in a2_verified
                    ),
                    "A4_traceable": sum(
                        bool(x.get("evidence_verified")) for x in a4_verified
                    ),
                    "A5_traceable": sum(
                        bool(x.get("evidence_verified")) for x in a5_verified
                    ),
                }

                results.append(result)

                detail_file.write(json.dumps({
                    **result,
                    "A2_findings": a2_findings,
                    "A4_graph_only_findings": a4_findings,
                    "A5_hybrid_findings": a5_findings,
                    "graph_edges_detail": edges,
                    "retrieval": [
                        {
                            "clause_id": x["id"],
                            "score": x.get("score"),
                        }
                        for x in retrieved
                    ],
                }, ensure_ascii=False) + "\n")

            except Exception as exc:
                errors.append({
                    "pair_id": row.get("pair_id"),
                    "error": f"{type(exc).__name__}: {exc}",
                })

            if index % 100 == 0:
                print(f"Processed {index}/{len(pairs)}")

    csv_path = OUT / "pair_results.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    summary = {
        "experiment": "Real-contract exploratory rule and graph comparison",
        "input_pairs": len(pairs),
        "processed_pairs": len(results),
        "errors": len(errors),
        "unique_documents": len(set(x["document_id"] for x in results)),
        "labels": "UNLABELED: no risk-detection precision/recall/F1 calculated",
        "relationship_counts": dict(Counter(x["relation"] for x in results)),
        "systems": {
            "A2_pairwise_rules": {
                "pairs_with_candidates": sum(x["A2_rule_candidates"] > 0 for x in results),
                "total_candidates": sum(x["A2_rule_candidates"] for x in results),
                "traceable_candidates": sum(x["A2_traceable"] for x in results),
            },
            "A4_graph_only": {
                "pairs_with_candidates": sum(x["A4_graph_candidates"] > 0 for x in results),
                "total_candidates": sum(x["A4_graph_candidates"] for x in results),
                "traceable_candidates": sum(x["A4_traceable"] for x in results),
            },
            "A5_hybrid": {
                "pairs_with_candidates": sum(x["A5_hybrid_candidates"] > 0 for x in results),
                "total_candidates": sum(x["A5_hybrid_candidates"] for x in results),
                "traceable_candidates": sum(x["A5_traceable"] for x in results),
            },
        },
        "retrieval": {
            "pairs_with_retrieved_clauses": sum(x["retrieved_count"] > 0 for x in results)
        },
        "limitations": [
            "CUAD category evidence is not cross-clause risk ground truth.",
            "Pairs are candidate combinations, not independent adjudicated cases.",
            "A1 retrieval is diagnostic only; no Gemini or LLM risk classifier was run.",
            "Candidate findings are not confirmed legal conflicts.",
            "Traceability is not semantic correctness."
        ],
    }

    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    (OUT / "errors.json").write_text(
        json.dumps(errors, indent=2), encoding="utf-8"
    )

    print("\n========== REAL CONTRACT EXPLORATION ==========")
    print(json.dumps(summary, indent=2))
    print("\nOutput directory:", OUT)

if __name__ == "__main__":
    main()
