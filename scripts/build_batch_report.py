import json
from collections import Counter
from pathlib import Path

source = Path("data/processed/cuad_annotation_batch_balanced.jsonl")
output = Path("data/processed/balanced_batch_report.txt")

with source.open(encoding="utf-8") as f:
    pairs = [json.loads(line) for line in f if line.strip()]

with output.open("w", encoding="utf-8") as f:
    f.write(f"TOTAL CANDIDATES: {len(pairs)}\n\n")

    for p in pairs:
        f.write(
            f"{p['candidate_id']} | {p['document_id']} | "
            f"{p['category_a']} <-> {p['category_b']}\n"
        )
        f.write(f"A: {p['evidence_a'][:350]}\n")
        f.write(f"B: {p['evidence_b'][:350]}\n\n")

print("Candidates:", len(pairs))
print("Contracts:", len(set(p["document_id"] for p in pairs)))
print("Report:", output)
