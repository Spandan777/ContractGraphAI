import json
from pathlib import Path

ids = {
    "PAIR-00185", "PAIR-00211", "PAIR-00207",
    "PAIR-00299", "PAIR-00302", "PAIR-00517",
    "PAIR-00507", "PAIR-00319", "PAIR-00086",
    "PAIR-00503", "PAIR-00418", "PAIR-00556"
}

source = Path("data/processed/cuad_candidate_pairs_clean.jsonl")
output = Path("data/processed/priority_review_12.txt")

with source.open(encoding="utf-8") as f:
    pairs = [json.loads(line) for line in f if line.strip()
             and json.loads(line)["candidate_id"] in ids]

with output.open("w", encoding="utf-8") as f:
    for p in pairs:
        f.write(f"\n{'='*80}\n")
        f.write(f"{p['candidate_id']} | {p['document_id']}\n")
        f.write(f"CATEGORY A: {p['category_a']}\n")
        f.write(p["context_a"] + "\n")
        f.write(f"\nCATEGORY B: {p['category_b']}\n")
        f.write(p["context_b"] + "\n")

print("Selected pairs:", len(pairs))
print("Output:", output)
