import csv
import json
import re
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

SOURCE = Path("data/processed/cuad_evidence_spans.jsonl")
OUT = Path("data/processed")

def normalize(value):
    return re.sub(r"[^a-z]", "", value.casefold())

def groups(category):
    c = normalize(category)
    result = set()

    if any(x in c for x in ["payment", "price", "fee", "revenue",
                             "minimumcommitment", "volume"]):
        result.add("payment")

    if any(x in c for x in ["termination", "renewal", "noticeperiod"]):
        result.add("termination")

    if any(x in c for x in ["liability", "indemn", "damages", "insurance"]):
        result.add("liability")

    if any(x in c for x in ["confidential", "noncompete",
                             "nonsolicitation", "nondisclosure"]):
        result.add("confidentiality")

    return result

with SOURCE.open(encoding="utf-8") as f:
    spans = [json.loads(line) for line in f if line.strip()]

by_document = defaultdict(list)
category_counts = Counter()

for span in spans:
    by_document[span["document_id"]].append(span)
    category_counts[span["category"]] += 1

pairs = []
pair_id = 0

for document_id, items in by_document.items():
    for a, b in combinations(items, 2):
        ga = groups(a["category"])
        gb = groups(b["category"])

        shared = ga & gb
        cross = ga | gb

        if shared:
            reason = "same_risk_domain"
        elif ("payment" in cross and "termination" in cross
              and len(cross) == 2):
            reason = "payment_termination"
        elif ("liability" in cross and "confidentiality" in cross
              and len(cross) == 2):
            reason = "liability_confidentiality"
        else:
            continue

        if a["span_id"] == b["span_id"]:
            continue

        pair_id += 1
        pairs.append({
            "candidate_id": f"PAIR-{pair_id:05}",
            "document_id": document_id,
            "span_a_id": a["span_id"],
            "span_b_id": b["span_id"],
            "category_a": a["category"],
            "category_b": b["category"],
            "candidate_reason": reason,
            "evidence_a": a["answer_text"],
            "evidence_b": b["answer_text"],
            "context_a": a["context_before"] + a["answer_text"] + a["context_after"],
            "context_b": b["context_before"] + b["answer_text"] + b["context_after"],
            "offsets_valid": a["offset_valid"] and b["offset_valid"],
            "label": "uncertain",
            "risk_type": "not_applicable",
            "severity": "not_applicable",
            "rationale": "",
            "review_status": "draft"
        })

OUT.mkdir(parents=True, exist_ok=True)

jsonl = OUT / "cuad_candidate_pairs.jsonl"
with jsonl.open("w", encoding="utf-8") as f:
    for pair in pairs:
        f.write(json.dumps(pair, ensure_ascii=False) + "\n")

csv_path = OUT / "cuad_candidate_pairs.csv"
if pairs:
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=pairs[0].keys())
        writer.writeheader()
        writer.writerows(pairs)

print("Evidence spans:", len(spans))
print("Documents:", len(by_document))
print("Candidate pairs:", len(pairs))
print("Pairs with valid offsets:", sum(p["offsets_valid"] for p in pairs))
print("\nCandidate categories:")
for category, count in category_counts.most_common():
    print(f"  {category}: {count}")
print("\nOutput:", jsonl)
