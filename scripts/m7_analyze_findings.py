import json
from pathlib import Path
from collections import Counter, defaultdict

path = Path("results/m7_real_contract_exploration/pair_findings.jsonl")

records = [
    json.loads(line)
    for line in path.read_text(encoding="utf-8").splitlines()
    if line.strip()
]

print("\n========== FINDINGS DISTRIBUTION ==========")

for system, field in [
    ("A2 RULES", "A2_findings"),
    ("A4 GRAPH ONLY", "A4_graph_only_findings"),
    ("A5 HYBRID", "A5_hybrid_findings")
]:
    types = Counter()
    relation_types = Counter()
    examples = defaultdict(list)

    for row in records:
        for finding in row.get(field, []):
            risk_type = finding.get("risk_type", "unspecified")
            types[risk_type] += 1
            relation_types[row.get("relation", "unknown")] += 1

            if len(examples[risk_type]) < 2:
                examples[risk_type].append({
                    "pair_id": row.get("pair_id"),
                    "document_id": row.get("document_id"),
                    "claim": finding.get("claim"),
                    "clauses": finding.get("clauses"),
                    "rationale": finding.get("rationale")
                })

    print(f"\n--- {system} ---")
    print("Risk types:")
    for key, value in types.most_common():
        print(f"  {key}: {value}")

    print("Representative findings:")
    for key, items in examples.items():
        print(f"\n  {key}:")
        for item in items:
            print(json.dumps(item, indent=2, ensure_ascii=False))

print("\n========== GRAPH RELATIONSHIP DISTRIBUTION ==========")
edge_types = Counter()

for row in records:
    for edge in row.get("graph_edges_detail", []):
        edge_types[edge.get("relation", edge.get("type", "unknown"))] += 1

for key, value in edge_types.most_common():
    print(f"{key}: {value}")

print("\n========== AUDIT COMPLETE ==========")
