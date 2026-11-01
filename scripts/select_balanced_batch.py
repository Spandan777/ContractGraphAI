import json
import random
from collections import Counter
from pathlib import Path

source = Path("data/processed/cuad_candidate_pairs_clean.jsonl")
output = Path("data/processed/cuad_annotation_batch_balanced.jsonl")

excluded = {
    "parties", "document name", "agreement date",
    "effective date", "expiration date", "governing law"
}

def norm(s):
    return " ".join(s.casefold().split())

with source.open(encoding="utf-8") as f:
    pairs = [json.loads(x) for x in f if x.strip()]

eligible = [
    p for p in pairs
    if norm(p["category_a"]) not in excluded
    and norm(p["category_b"]) not in excluded
]

random.Random(42).shuffle(eligible)

selected = []
documents = Counter()
category_pairs = Counter()

for p in eligible:
    doc = p["document_id"]
    cats = tuple(sorted((norm(p["category_a"]), norm(p["category_b"]))))

    if documents[doc] >= 2 or category_pairs[cats] >= 4:
        continue

    selected.append(p)
    documents[doc] += 1
    category_pairs[cats] += 1

    if len(selected) == 40:
        break

with output.open("w", encoding="utf-8") as f:
    for p in selected:
        f.write(json.dumps(p, ensure_ascii=False) + "\n")

print("Clean candidates:", len(pairs))
print("Eligible candidates:", len(eligible))
print("Selected candidates:", len(selected))
print("Contracts represented:", len(documents))
print("Maximum pairs per contract:", max(documents.values(), default=0))
print("Maximum repeated category combinations:", max(category_pairs.values(), default=0))
print("Output:", output)
