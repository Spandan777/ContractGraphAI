import json
import re
from pathlib import Path

source = Path("data/processed/cuad_candidate_pairs.jsonl")
output = Path("data/processed/cuad_candidate_pairs_clean.jsonl")

def norm(text):
    return re.sub(r"\s+", " ", text).strip().casefold()

seen = set()
clean = []
removed_identical = 0
removed_duplicate = 0
removed_invalid = 0

with source.open(encoding="utf-8") as f:
    for line in f:
        if not line.strip():
            continue

        p = json.loads(line)

        if not p.get("offsets_valid"):
            removed_invalid += 1
            continue

        a, b = norm(p["evidence_a"]), norm(p["evidence_b"])

        if not a or not b or a == b:
            removed_identical += 1
            continue

        key = (p["document_id"], *sorted((a, b)))

        if key in seen:
            removed_duplicate += 1
            continue

        seen.add(key)
        clean.append(p)

with output.open("w", encoding="utf-8") as f:
    for p in clean:
        f.write(json.dumps(p, ensure_ascii=False) + "\n")

print("Original candidates:", len(seen) + removed_identical + removed_duplicate + removed_invalid)
print("Clean candidates:", len(clean))
print("Identical evidence removed:", removed_identical)
print("Duplicate combinations removed:", removed_duplicate)
print("Invalid offsets removed:", removed_invalid)
print("Output:", output)
