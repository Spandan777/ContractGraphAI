import sys
import re
import json
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from contractgraph.risks import detect_cross_clause_risks
from contractgraph.graph import build_dependency_graph, edges_as_dicts
from contractgraph.cross_clause_reasoning import detect_cross_clause_findings

# Synthetic controlled test cases.
# Labels are predefined for this pilot, not taken from model predictions.

CASES = [
    {
        "id": "P01", "gold": "risk",
        "a": ("Payment A", "Payment of each invoice is due within 30 days after receipt.", ["payment"]),
        "b": ("Payment B", "The customer shall pay each invoice within 60 days after receipt.", ["payment"]),
    },
    {
        "id": "P02", "gold": "risk",
        "a": ("Termination A", "Either party may terminate this agreement upon 30 days' written notice.", ["termination"]),
        "b": ("Termination B", "Either party may terminate this agreement upon 60 days' written notice.", ["termination"]),
    },
    {
        "id": "P03", "gold": "risk",
        "a": ("Confidentiality A", "Confidentiality obligations shall survive termination for 3 years.", ["confidentiality"]),
        "b": ("Confidentiality B", "Confidentiality obligations shall survive termination for 5 years.", ["confidentiality"]),
    },
    {
        "id": "P04", "gold": "risk",
        "a": ("Liability A", "Aggregate liability shall not exceed $100,000 for all claims.", ["liability"]),
        "b": ("Liability B", "Aggregate liability shall not exceed $1,000,000 for all claims.", ["liability"]),
    },
    {
        "id": "P05", "gold": "risk",
        "a": ("Liability A", "The supplier's aggregate liability shall be unlimited.", ["liability"]),
        "b": ("Records B", "The parties shall maintain accurate project records.", []),
    },
    {
        "id": "P06", "gold": "risk",
        "a": ("Termination A", "The customer may terminate this agreement immediately without prior notice.", ["termination"]),
        "b": ("Payment B", "The customer shall pay undisputed invoices within 30 days.", ["payment"]),
    },
    {
        "id": "N01", "gold": "no_risk",
        "a": ("Termination A", "Either party may terminate this agreement with 30 days' written notice.", ["termination"]),
        "b": ("Renewal B", "This agreement automatically renews for successive twelve month terms.", ["termination"]),
    },
    {
        "id": "N02", "gold": "no_risk",
        "a": ("Payment A", "The customer shall pay invoices within 30 business days.", ["payment"]),
        "b": ("Payment B", "The customer shall pay invoices within 60 calendar days.", ["payment"]),
    },
    {
        "id": "N03", "gold": "no_risk",
        "a": ("Payment A", "Invoices are payable within 30 days after receipt.", ["payment"]),
        "b": ("Payment B", "Payment of invoices is due within 30 days after receipt.", ["payment"]),
    },
    {
        "id": "N04", "gold": "no_risk",
        "a": ("Payment A", "Invoices are payable within 30 days.", ["payment"]),
        "b": ("Confidentiality B", "Confidentiality obligations survive termination for 5 years.", ["confidentiality"]),
    },
    {
        "id": "N05", "gold": "no_risk",
        "a": ("Termination A", "Either party may terminate for cause if a breach remains uncured within 30 days.", ["termination"]),
        "b": ("Termination B", "Either party may terminate for cause if a breach remains uncured within 30 days.", ["termination"]),
    },
    {
        "id": "N06", "gold": "no_risk",
        "a": ("Liability A", "Aggregate liability for direct damages shall not exceed $100,000.", ["liability"]),
        "b": ("Liability B", "Liability for intellectual property claims is excluded from the foregoing cap.", ["liability"]),
    },
]

# A1: Independent single-clause risk assessment.
# This is a deterministic proxy, NOT a completed RAG/LLM baseline.
INDEPENDENT_RISK_PATTERNS = [
    re.compile(r"\bliability\b.{0,60}\b(unlimited|uncapped)\b", re.I),
    re.compile(
        r"\bterminate\b.{0,80}\bimmediately\b.{0,40}\bwithout (?:prior )?notice\b",
        re.I,
    ),
]

def a1_independent(clause_a, clause_b):
    return any(
        pattern.search(clause["text"])
        for clause in (clause_a, clause_b)
        for pattern in INDEPENDENT_RISK_PATTERNS
    )

def a4_graph_reasoning(clause_a, clause_b):
    clauses = [clause_a, clause_b]
    rule_findings = detect_cross_clause_risks(clauses)
    graph = build_dependency_graph(clauses)
    edges = edges_as_dicts(graph)
    findings = detect_cross_clause_findings(
        clauses, edges, rule_findings
    )
    return bool(findings), findings, edges

def metrics(rows, prediction_key):
    tp = sum(r["gold"] == "risk" and r[prediction_key] == "risk" for r in rows)
    fp = sum(r["gold"] == "no_risk" and r[prediction_key] == "risk" for r in rows)
    fn = sum(r["gold"] == "risk" and r[prediction_key] == "no_risk" for r in rows)
    tn = sum(r["gold"] == "no_risk" and r[prediction_key] == "no_risk" for r in rows)

    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
    accuracy = (tp + tn) / len(rows) if rows else 0

    return {
        "TP": tp, "FP": fp, "FN": fn, "TN": tn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "accuracy": round(accuracy, 4),
    }

results = []

for case in CASES:
    a = {
        "id": "A", "title": case["a"][0],
        "text": case["a"][1], "aspects": case["a"][2], "index": 1,
    }
    b = {
        "id": "B", "title": case["b"][0],
        "text": case["b"][1], "aspects": case["b"][2], "index": 2,
    }

    a1 = a1_independent(a, b)
    a4, findings, edges = a4_graph_reasoning(a, b)

    results.append({
        "pair_id": case["id"],
        "gold": case["gold"],
        "A1_prediction": "risk" if a1 else "no_risk",
        "A4_prediction": "risk" if a4 else "no_risk",
        "A4_candidate_count": len(findings),
        "A4_risk_types": ";".join(sorted(set(
            f.get("risk_type", "") for f in findings
        ))),
        "graph_edge_count": len(edges),
    })

out = ROOT / "results" / "m7_controlled_pilot"
out.mkdir(parents=True, exist_ok=True)

with (out / "predictions.csv").open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
    writer.writeheader()
    writer.writerows(results)

summary = {
    "experiment": "Controlled synthetic A1/A4 pilot",
    "number_of_pairs": len(results),
    "gold_label_counts": {
        label: sum(r["gold"] == label for r in results)
        for label in ("risk", "no_risk")
    },
    "A1_independent_clause_proxy": metrics(results, "A1_prediction"),
    "A4_graph_reasoning": metrics(results, "A4_prediction"),
    "important_limitation": (
        "Synthetic pilot only. A1 is an independent-clause heuristic proxy, "
        "not a full RAG/LLM baseline. A4 outputs are review candidates, "
        "not confirmed legal conflicts. Not suitable as empirical research evidence."
    ),
}

(out / "summary.json").write_text(
    json.dumps(summary, indent=2), encoding="utf-8"
)

print("\n========== CONTROLLED A1 vs A4 PILOT ==========")
print(json.dumps(summary, indent=2))

print("\n========== PAIR-LEVEL PREDICTIONS ==========")
for r in results:
    print(
        f'{r["pair_id"]}: GOLD={r["gold"]:<7} '
        f'A1={r["A1_prediction"]:<7} '
        f'A4={r["A4_prediction"]:<7} '
        f'Candidates={r["A4_candidate_count"]}'
    )

print(f"\nSaved results to: {out}")
print("Files: predictions.csv, summary.json")
