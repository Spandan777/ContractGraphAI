import csv
import json
from pathlib import Path

BASE = Path(".")
JSON_PATH = BASE / "data/raw/cuad/CUAD_v1/CUAD_v1.json"
PILOT_PATH = BASE / "data/processed/cuad_pilot_30.csv"
OUT = BASE / "data/processed"

with JSON_PATH.open(encoding="utf-8") as f:
    cuad = json.load(f)

with PILOT_PATH.open(encoding="utf-8-sig") as f:
    pilot = list(csv.DictReader(f))

lookup = {item["title"]: item for item in cuad["data"]}
records = []
summary = []

for index, row in enumerate(pilot, start=1):
    title = row["title"]
    document = lookup.get(title)

    if not document:
        summary.append({"document_id": f"CUAD-{index:03}", "title": title,
                        "status": "missing_json", "spans": 0})
        continue

    document_id = f"CUAD-{index:03}"
    count = 0

    for paragraph in document.get("paragraphs", []):
        context = paragraph.get("context", "")

        for question in paragraph.get("qas", []):
            category = question["id"].split("__")[-1]

            for answer_index, answer in enumerate(question.get("answers", []), 1):
                text = answer.get("text", "")
                start = answer.get("answer_start", -1)

                if not text or not isinstance(start, int):
                    continue

                end = start + len(text)
                valid = context[start:end] == text

                records.append({
                    "span_id": f"{document_id}-S{count + 1:04}",
                    "document_id": document_id,
                    "document_title": title,
                    "category": category,
                    "answer_index": answer_index,
                    "start_char": start,
                    "end_char": end,
                    "answer_text": text,
                    "offset_valid": valid,
                    "context_before": context[max(0, start - 500):start],
                    "context_after": context[end:min(len(context), end + 500)],
                    "pdf_path": row["pdf_path"]
                })
                count += 1

    summary.append({
        "document_id": document_id,
        "title": title,
        "status": "processed",
        "spans": count,
        "valid_offsets": sum(
            1 for x in records
            if x["document_id"] == document_id and x["offset_valid"]
        )
    })

OUT.mkdir(parents=True, exist_ok=True)

with (OUT / "cuad_evidence_spans.jsonl").open("w", encoding="utf-8") as f:
    for record in records:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

if records:
    with (OUT / "cuad_evidence_spans.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.DictWriter(f, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)

with (OUT / "cuad_extraction_summary.json").open("w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)

print("Documents processed:", sum(x["status"] == "processed" for x in summary))
print("Evidence spans extracted:", len(records))
print("Valid offsets:", sum(x["offset_valid"] for x in records))
print("Invalid offsets:", sum(not x["offset_valid"] for x in records))
print("Output: data/processed/cuad_evidence_spans.jsonl")
