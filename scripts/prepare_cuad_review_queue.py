from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

JSON_PATH = ROOT / "data/raw/cuad/CUAD_v1/CUAD_v1.json"
PILOT_PATH = ROOT / "data/processed/cuad_pilot_30.csv"
SPANS_PATH = ROOT / "data/processed/cuad_evidence_spans.jsonl"
BATCH_PATH = ROOT / "data/processed/cuad_annotation_batch_balanced.jsonl"

OUT_DIR = ROOT / "data/annotations"
ENRICHED_SPANS = ROOT / "data/processed/cuad_evidence_spans_with_paragraphs.jsonl"
ENRICHED_BATCH = ROOT / "data/processed/cuad_annotation_batch_with_context.jsonl"
QUEUE_PATH = OUT_DIR / "cuad_review_queue.jsonl"
GUIDE_PATH = OUT_DIR / "ANNOTATION_GUIDE.md"


def read_jsonl(path):
    with path.open("r", encoding="utf-8-sig") as f:
        return [json.loads(line) for line in f if line.strip()]


def main():
    for path in (JSON_PATH, PILOT_PATH, SPANS_PATH, BATCH_PATH):
        if not path.exists():
            raise FileNotFoundError(f"Required input missing: {path}")

    cuad = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    with PILOT_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        pilot = list(csv.DictReader(f))

    documents = {item["title"]: item for item in cuad.get("data", [])}
    reconstructed = {}
    missing_documents = []

    for index, row in enumerate(pilot, start=1):
        title = row["title"]
        document = documents.get(title)

        if document is None:
            missing_documents.append(title)
            continue

        document_id = f"CUAD-{index:03}"
        span_number = 0

        for paragraph in document.get("paragraphs", []):
            context = paragraph.get("context", "")

            for question in paragraph.get("qas", []):
                category = question.get("id", "").split("__")[-1]

                for answer_index, answer in enumerate(
                    question.get("answers", []), start=1
                ):
                    answer_text = answer.get("text", "")
                    start = answer.get("answer_start", -1)

                    if not answer_text or not isinstance(start, int):
                        continue

                    span_number += 1
                    end = start + len(answer_text)

                    span_id = f"{document_id}-S{span_number:04}"

                    reconstructed[span_id] = {
                        "document_id": document_id,
                        "document_title": title,
                        "category": category,
                        "answer_index": answer_index,
                        "start_char": start,
                        "end_char": end,
                        "answer_text": answer_text,
                        "offset_valid": context[start:end] == answer_text,
                        "paragraph_context": context,
                        "paragraph_length": len(context),
                    }

    original_spans = read_jsonl(SPANS_PATH)
    original_ids = {item["span_id"] for item in original_spans}

    missing_ids = original_ids - set(reconstructed)

    if missing_ids:
        raise RuntimeError(
            f"Could not reconstruct {len(missing_ids)} span IDs. "
            "No outputs were written."
        )

    enriched_spans = []

    for item in original_spans:
        enriched_spans.append({
            **item,
            **reconstructed[item["span_id"]]
        })

    with ENRICHED_SPANS.open("w", encoding="utf-8") as f:
        for item in enriched_spans:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    span_by_id = {item["span_id"]: item for item in enriched_spans}
    batch = read_jsonl(BATCH_PATH)

    enriched_pairs = []
    queue = []

    for pair in batch:
        a = span_by_id.get(pair["span_a_id"])
        b = span_by_id.get(pair["span_b_id"])

        if a is None or b is None:
            raise RuntimeError(
                f"Missing source span for {pair.get('candidate_id')}"
            )

        enriched_pairs.append({
            **pair,
            "source_a": {
                "span_id": a["span_id"],
                "category": a["category"],
                "answer_text": a["answer_text"],
                "start_char": a["start_char"],
                "end_char": a["end_char"],
                "offset_valid": a["offset_valid"],
                "paragraph_context": a["paragraph_context"],
            },
            "source_b": {
                "span_id": b["span_id"],
                "category": b["category"],
                "answer_text": b["answer_text"],
                "start_char": b["start_char"],
                "end_char": b["end_char"],
                "offset_valid": b["offset_valid"],
                "paragraph_context": b["paragraph_context"],
            },
        })

        queue.append({
            "candidate_id": pair["candidate_id"],
            "document_id": pair["document_id"],
            "evidence_span_a_id": a["span_id"],
            "evidence_span_b_id": b["span_id"],
            "category_a": a["category"],
            "category_b": b["category"],
            "candidate_reason": pair.get("candidate_reason", ""),
            "evidence_a": a["answer_text"],
            "evidence_b": b["answer_text"],
            "paragraph_context_a": a["paragraph_context"],
            "paragraph_context_b": b["paragraph_context"],
            "start_a": a["start_char"],
            "end_a": a["end_char"],
            "start_b": b["start_char"],
            "end_b": b["end_char"],
            "offsets_valid": bool(
                a["offset_valid"] and b["offset_valid"]
            ),
            "label": None,
            "risk_type": None,
            "severity": None,
            "rationale": "",
            "scope_analysis": "",
            "trigger_analysis": "",
            "exception_analysis": "",
            "precedence_analysis": "",
            "annotator": "",
            "review_status": "pending_human_review",
        })

    with ENRICHED_BATCH.open("w", encoding="utf-8") as f:
        for item in enriched_pairs:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with QUEUE_PATH.open("w", encoding="utf-8") as f:
        for item in queue:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    GUIDE_PATH.write_text(
        """# CUAD Cross-Clause Annotation Guide

This is a review queue, not a gold-labelled dataset.
All labels are intentionally blank.

## Unit of annotation

Review both CUAD evidence spans and their full source paragraph contexts.
Answer spans may not represent complete contractual clauses.
Inspect the surrounding contract before assigning a label.

## Labels

- risk: Actual incompatible obligations, rights, restrictions,
  exceptions, triggers, durations, remedies or precedence problems.
- no_risk: Provisions are compatible, address distinct subjects,
  or expressly reconcile their interaction.
- uncertain: Available context is insufficient or requires
  interpretation beyond this annotation protocol.

## Required review

Record rationale, risk type and severity for risk findings.
Assess scope, trigger, exceptions and precedence.
Cite exact source text.

Do not infer a conflict merely because two durations or categories differ.

## Quality controls

- Preserve uncertain labels when evidence is insufficient.
- Independently review a subset with a second annotator.
- Adjudicate disagreements.
- Split datasets by document_id, never by candidate pair.
- CUAD categories are not cross-clause conflict labels.
- Never use draft or AI-assisted labels as gold evaluation data.
""",
        encoding="utf-8",
    )

    print("CONTEXT ENRICHMENT COMPLETED")
    print("=" * 40)
    print(f"Evidence spans: {len(enriched_spans)}")
    print(f"Candidate pairs: {len(enriched_pairs)}")
    print(f"Review queue records: {len(queue)}")
    print(
        "Valid-offset pairs:",
        sum(item["offsets_valid"] for item in queue)
    )
    print(f"Missing pilot documents: {len(missing_documents)}")
    print(f"Review queue: {QUEUE_PATH}")
    print(f"Annotation guide: {GUIDE_PATH}")


if __name__ == "__main__":
    main()
