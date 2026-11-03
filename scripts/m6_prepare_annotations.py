import argparse
from pathlib import Path
from contractgraph.m6_annotations import read_jsonl, write_jsonl

p = argparse.ArgumentParser(description="Create an independent human annotation sheet from the M6 review queue")
p.add_argument("--queue", default="data/annotations/cuad_review_queue.jsonl")
p.add_argument("--annotator", required=True)
p.add_argument("--output", required=True)
a = p.parse_args()
queue = read_jsonl(a.queue)
rows = []
for q in queue:
    rows.append({
        "candidate_id": q["candidate_id"], "document_id": q["document_id"],
        "evidence_span_a_id": q["evidence_span_a_id"], "evidence_span_b_id": q["evidence_span_b_id"],
        "category_a": q.get("category_a", ""), "category_b": q.get("category_b", ""),
        "candidate_reason": q.get("candidate_reason", ""),
        "evidence_a": q.get("evidence_a", ""), "evidence_b": q.get("evidence_b", ""),
        "paragraph_context_a": q.get("paragraph_context_a", ""),
        "paragraph_context_b": q.get("paragraph_context_b", ""),
        "start_a": q.get("start_a"), "end_a": q.get("end_a"),
        "start_b": q.get("start_b"), "end_b": q.get("end_b"),
        "offsets_valid": q.get("offsets_valid", False),
        "label": None, "risk_type": None, "severity": None,
        "rationale": "", "scope_analysis": "", "trigger_analysis": "",
        "exception_analysis": "", "precedence_analysis": "",
        "annotator": a.annotator, "review_status": "pending_human_review",
        "adjudicator": "", "adjudication_notes": "",
    })
write_jsonl(a.output, rows)
print(f"Created {len(rows)} blank annotation records: {a.output}")
print("No labels were generated. Complete the fields independently as a human annotator.")
