import json
import random
from collections import defaultdict
from pathlib import Path

source = Path("data/processed/cuad_candidate_pairs.jsonl")
output = Path("data/processed/cuad_annotation_batch_40.jsonl")

with source.open(encoding="utf-8") as f:
    pairs = [json.loads(line) for line in f if line.strip()]

# Exclude administrative categories from the first annotation batch.
excluded = {
    "parties", "document name", "agreement date",
    "effective date", "expiration date", "governing law"
}

def norm(s):
    return s.casefold().strip()

eligible = [
    p for p in pairs
    if norm(p["category_a"]) not in excluded
    and norm(p["category_b"]) not in excluded
]

# Prioritize pairs involving substantive risk categories.
priority_terms = (
    "liability", "termination", "renewal", "commitment",
    "revenue", "profit", "insurance", "damages",
    "license", "assignment", "ownership", "notice",
    "restriction", "exclusivity", "warranty"
)

def priority(pair):
    text = (pair["category_a"] + " " + pair["category_b"]).casefold()
    return sum(term in text for term in priority_terms)

eligible.sort(key=priority, reverse=True)

# Limit repeated pairs from the same contract.
random.seed(42)
random.shuffle(eligible)
eligible.sort(key=priority, reverse=True)

selected = []
per_document = defaultdict(int)

for pair in eligible:
    doc = pair["document_id"]
    if per_document[doc] >= 3:
        continue
    selected.append(pair)
    per_document[doc] += 1
    if len(selected) == 40:
        break

with output.open("w", encoding="utf-8") as f:
    for pair in selected:
        f.write(json.dumps(pair, ensure_ascii=False) + "\n")

print("Eligible candidate pairs:", len(eligible))
print("Selected for annotation:", len(selected))
print("Contracts represented:", len(per_document))
print("Output:", output)
print("\nSelected category pairs:")
for p in selected:
    print(
        p["candidate_id"], "|",
        p["document_id"], "|",
        p["category_a"], "<->", p["category_b"]
    )
