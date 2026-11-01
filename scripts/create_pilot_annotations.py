import json
from pathlib import Path

BASE = Path("data/processed")
SOURCE = BASE / "cuad_candidate_pairs.jsonl"
OUTPUT = Path("data/annotations/pilot_annotations_draft.jsonl")

decisions = {
    "PAIR-00082": (
        "uncertain",
        "The royalty provisions and post-termination marketing authorisation transfer obligations concern different duties. The available excerpts do not establish whether any royalty obligation conflicts with the transfer requirements."
    ),
    "PAIR-00083": (
        "no_risk",
        "Section 19.7(ii) expressly permits a six-month sell-off period and requires reporting and royalty payments during that period. The post-termination provision preserves the relevant payment obligation."
    ),
    "PAIR-00084": (
        "uncertain",
        "Royalty payments and transition-out obligations both apply to the contractual relationship. The available excerpts do not establish incompatible timing, scope, or responsibilities."
    ),
    "PAIR-00112": (
        "uncertain",
        "The agreement provides a termination-for-convenience right alongside royalty provisions. The available excerpts do not establish whether royalty obligations survive or conflict with termination."
    ),
    "PAIR-00511": (
        "no_risk",
        "Section 6.3 preserves specified obligations, including royalty-related provisions, when the Services Term ends but the overall agreement remains active. The provisions distinguish termination of the Services Term from termination of the agreement."
    ),
    "PAIR-00322": (
        "no_risk",
        "The renewal provisions and the termination right following failure to achieve sales milestones describe separate contractual mechanisms. No incompatible obligation is established by the supplied text."
    ),
    "PAIR-00518": (
        "no_risk",
        "Automatic renewal subject to advance non-renewal notice can coexist with a separate right to terminate without cause on 90 days' notice. No direct contradiction is established."
    ),
    "PAIR-00523": (
        "no_risk",
        "The liability limitation and insurance-maintenance obligation address different contractual subjects. The insurance requirement does not itself override or contradict the stated liability cap."
    )
}

with SOURCE.open(encoding="utf-8") as f:
    candidates = {}
    for line in f:
        if line.strip():
            item = json.loads(line)
            candidates[item["candidate_id"]] = item
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
written = []

for candidate_id, (label, rationale) in decisions.items():
    p = candidates[candidate_id]

    written.append({
        "annotation_id": f"ANN-PILOT-{candidate_id[-5:]}",
        "document_id": p["document_id"],
        "clause_a_id": p["span_a_id"],
        "clause_b_id": p["span_b_id"],
        "label": label,
        "risk_type": "not_applicable",
        "severity": "not_applicable",
        "rationale": rationale,
        "evidence_a": p["evidence_a"],
        "evidence_b": p["evidence_b"],
        "scope": "Requires complete contractual clause review.",
        "trigger": "See source evidence and surrounding contractual context.",
        "exception": "Not established by the reviewed excerpts.",
        "precedence": "Not established by the reviewed excerpts.",
        "annotator": "AI_ASSISTED_REVIEW_PENDING_HUMAN",
        "review_status": "draft",
        "candidate_id": candidate_id
    })

with OUTPUT.open("w", encoding="utf-8") as f:
    for item in written:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")

print("Annotation records created:", len(written))
print("No risk:", sum(x["label"] == "no_risk" for x in written))
print("Uncertain:", sum(x["label"] == "uncertain" for x in written))
print("Risk:", sum(x["label"] == "risk" for x in written))
print("Status: draft, pending human verification")
print("Output:", OUTPUT)
