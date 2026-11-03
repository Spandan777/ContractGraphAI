import ast
import csv
import json
from pathlib import Path
from collections import Counter, defaultdict

pair_path = Path("data/processed/m7_real_contract_pairs.jsonl")
csv_path = Path("data/raw/cuad/CUAD_v1/master_clauses.csv")

documents = defaultdict(list)

with csv_path.open(encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        filename = row["Filename"]

        for category, value in row.items():
            if category.endswith("-Answer"):
                continue

            try:
                spans = ast.literal_eval(value) if value else []
            except (ValueError, SyntaxError):
                continue

            if isinstance(spans, list):
                for span in spans:
                    if isinstance(span, str) and span.strip():
                        documents[filename].append({
                            "category": category,
                            "text": span.strip()
                        })

pairs = [
    json.loads(line)
    for line in pair_path.read_text(encoding="utf-8").splitlines()
    if line.strip()
]

matched = 0
missing = []
counts = []

for pair in pairs:
    doc = pair["document_id"]
    if doc in documents:
        matched += 1
        counts.append(len(documents[doc]))
    else:
        missing.append(doc)

print("========== RETRIEVAL CORPUS AUDIT ==========")
print("Input pairs:", len(pairs))
print("Matched pairs:", matched)
print("Unmatched pairs:", len(missing))
print("Unique documents:", len(set(p["document_id"] for p in pairs)))
print("Documents with CUAD evidence:", len(documents))
print("Average evidence spans per matched pair:", round(sum(counts)/len(counts), 2) if counts else 0)
print("Maximum evidence spans:", max(counts) if counts else 0)
print("Minimum evidence spans:", min(counts) if counts else 0)
print("Sample unmatched documents:", missing[:5])
