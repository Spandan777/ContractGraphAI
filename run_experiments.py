import csv
import json
from pathlib import Path

from src.contractgraph.sample_data import SAMPLE_CONTRACT
from src.contractgraph.clauses import split_clauses
from src.contractgraph.retrieval import retrieve
from src.contractgraph.graph import build_dependency_graph, edges_as_dicts
from src.contractgraph.risks import detect_cross_clause_risks
from src.contractgraph.evidence import verify_evidence
from src.contractgraph.ablation import ABLATIONS

QUERIES = {
    "payment": "payment invoice fees deadline",
    "termination": "termination expiry notice period",
    "liability": "liability indemnification damages limitation cap",
    "confidentiality": "confidential information disclosure duration",
}

def main():
    output_dir = Path("results")
    output_dir.mkdir(exist_ok=True)

    clauses = split_clauses(SAMPLE_CONTRACT)
    clause_map = {c["id"]: c for c in clauses}

    graph = build_dependency_graph(clauses)
    graph_edges = edges_as_dicts(graph)

    retrieval_results = {
        name: retrieve(query, clauses, 3)
        for name, query in QUERIES.items()
    }

    rule_findings = detect_cross_clause_risks(clauses)
    verified_findings = verify_evidence(rule_findings, clause_map)

    experiments = []

    # A1: Independent retrieval
    a1 = {
        "id": "A1",
        "system": ABLATIONS[0][1],
        "retrieved_clauses": {
            k: [c["id"] for c in v]
            for k, v in retrieval_results.items()
        },
        "retrieval_count": sum(len(v) for v in retrieval_results.values()),
    }
    experiments.append(a1)

    # A2: Retrieval + aspect tagging
    a2 = {
        "id": "A2",
        "system": ABLATIONS[1][1],
        "retrieved_clauses": {
            k: [
                {"id": c["id"], "aspects": c.get("aspects", [])}
                for c in v
            ]
            for k, v in retrieval_results.items()
        },
        "tagged_clause_count": sum(bool(c.get("aspects")) for c in clauses),
    }
    experiments.append(a2)

    # A3: Retrieval + graph candidates
    a3 = {
        "id": "A3",
        "system": ABLATIONS[2][1],
        "graph_nodes": len(clauses),
        "graph_edges": len(graph_edges),
        "candidate_edges": [
            e for e in graph_edges
            if e.get("relation") == "potential_conflict"
        ],
    }
    experiments.append(a3)

    # A4: Graph + cross-clause rules
    a4 = {
        "id": "A4",
        "system": ABLATIONS[3][1],
        "graph_edges": len(graph_edges),
        "risk_candidate_count": len(rule_findings),
        "risk_candidates": rule_findings,
    }
    experiments.append(a4)

    # A5: Full pipeline + evidence traceability
    a5 = {
        "id": "A5",
        "system": ABLATIONS[4][1],
        "risk_candidate_count": len(verified_findings),
        "verified_count": sum(
            f.get("evidence_verified", False)
            for f in verified_findings
        ),
        "findings": verified_findings,
    }
    experiments.append(a5)

    # Save detailed JSON
    report = {
        "project": "ContractGraph AI",
        "dataset": "Synthetic demonstration contract",
        "document_count": 1,
        "clause_count": len(clauses),
        "experiments": experiments,
        "graph_edges": graph_edges,
        "limitations": [
            "Synthetic demonstration only",
            "No human-reviewed gold labels",
            "Precision, recall and F1 not calculated",
            "Evidence verification checks source traceability, not semantic entailment"
        ]
    }

    with open(output_dir / "ablation_results.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Save CSV summary
    csv_rows = []
    for exp in experiments:
        csv_rows.append({
            "experiment": exp["id"],
            "system": exp["system"],
            "clauses": len(clauses),
            "retrieval_count": exp.get("retrieval_count", ""),
            "graph_edges": exp.get("graph_edges", ""),
            "risk_candidates": exp.get("risk_candidate_count", ""),
            "evidence_verified": exp.get("verified_count", ""),
            "precision": "",
            "recall": "",
            "f1": "",
            "status": "functional_demo_only_no_gold_labels"
        })

    with open(output_dir / "ablation_results.csv", "w",
              newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_rows[0].keys())
        writer.writeheader()
        writer.writerows(csv_rows)

    # Save readable summary
    with open(output_dir / "experiment_summary.txt", "w",
              encoding="utf-8") as f:
        f.write("CONTRACTGRAPH AI - ABLATION EXPERIMENTS\n")
        f.write("=" * 48 + "\n\n")
        f.write(f"Documents: 1 (synthetic)\n")
        f.write(f"Clauses: {len(clauses)}\n")
        f.write(f"Graph edges: {len(graph_edges)}\n")
        f.write(f"Risk candidates: {len(rule_findings)}\n")
        f.write(
            f"Evidence traceable: "
            f"{sum(x.get('evidence_verified', False) for x in verified_findings)}"
            f"/{len(verified_findings)}\n\n"
        )

        for exp in experiments:
            f.write(f"{exp['id']}: {exp['system']}\n")

        f.write("\nIMPORTANT: These are functional demonstration outputs, ")
        f.write("not benchmark performance measurements.\n")

    print("\nCONTRACTGRAPH AI EXPERIMENTS COMPLETED")
    print("=" * 45)
    print(f"Clauses: {len(clauses)}")
    print(f"Graph edges: {len(graph_edges)}")
    print(f"Risk candidates: {len(rule_findings)}")
    print(
        f"Evidence verified: "
        f"{sum(x.get('evidence_verified', False) for x in verified_findings)}"
        f"/{len(verified_findings)}"
    )
    print("\nA1-A5 completed.")
    print("Results saved in:", output_dir.resolve())

if __name__ == "__main__":
    main()
