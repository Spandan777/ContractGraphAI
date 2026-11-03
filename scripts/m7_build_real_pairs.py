import pandas as pd
import ast
import json
import re
from pathlib import Path

SOURCE = Path("data/raw/cuad/CUAD_v1/master_clauses.csv")
OUTPUT = Path("data/processed/m7_real_contract_pairs.jsonl")

df = pd.read_csv(SOURCE).fillna("")

def norm(value):
    return re.sub(r"\s+", " ", str(value)).strip().lower()

def find_column(name):
    target = norm(name)
    for col in df.columns:
        if norm(col) == target:
            return col
    return None

def extract_spans(value):
    if not value or str(value).strip() in ("", "[]"):
        return []

    try:
        parsed = ast.literal_eval(str(value))
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
        return [str(parsed).strip()]
    except (ValueError, SyntaxError):
        return [str(value).strip()]

relationships = [
    ("Cap On Liability", "Uncapped Liability", "liability"),
    ("Termination For Convenience", "Post-Termination Services", "termination"),
    ("Revenue/Profit Sharing", "Post-Termination Services", "payment_termination"),
    ("Renewal Term", "Notice Period To Terminate Renewal", "renewal_termination"),
]

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

records = []
pair_number = 0

for _, row in df.iterrows():
    filename = str(row["Filename"])

    for cat_a, cat_b, relation in relationships:
        col_a = find_column(cat_a)
        col_b = find_column(cat_b)

        if not col_a or not col_b:
            continue

        spans_a = extract_spans(row[col_a])
        spans_b = extract_spans(row[col_b])

        for a_index, text_a in enumerate(spans_a):
            for b_index, text_b in enumerate(spans_b):
                if not text_a or not text_b:
                    continue

                pair_number += 1

                records.append({
                    "pair_id": f"CUADPAIR-{pair_number:06d}",
                    "document_id": filename,
                    "category_a": cat_a,
                    "category_b": cat_b,
                    "relation": relation,
                    "clause_a": text_a,
                    "clause_b": text_b,
                    "label": "unlabeled",
                    "label_source": "CUAD category evidence only"
                })

with OUTPUT.open("w", encoding="utf-8") as f:
    for record in records:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

print("\n========== REAL CONTRACT PAIR DATASET ==========")
print("Contracts:", df["Filename"].nunique())
print("Candidate pairs:", len(records))
print("Unique contracts represented:", len(set(x["document_id"] for x in records)))
print("\nRelationship distribution:")

from collections import Counter
for key, value in Counter(x["relation"] for x in records).items():
    print(key, ":", value)

print("\nOutput:", OUTPUT)
print("Labels: All pairs remain explicitly UNLABELED.")
