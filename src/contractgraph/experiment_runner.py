"""Reproducible A1-A5 ablation evaluation for ContractGraphAI.

This module deliberately refuses to calculate benchmark metrics from draft,
unreviewed, uncertain, or malformed annotations.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from .evaluation import classification_metrics

SYSTEMS = [
    ("A1", "Independent retrieval"),
    ("A2", "Retrieval + aspect analysis"),
    ("A3", "Retrieval + graph candidates"),
    ("A4", "Graph + cross-clause reasoning"),
    ("A5", "Full system + evidence verification"),
]
VALID_LABELS = {"risk", "no_risk"}
UNCERTAIN_LABEL = "uncertain"


def _first(record: dict, names: tuple[str, ...], default=None):
    for name in names:
        if name in record and record[name] is not None:
            return record[name]
    return default


def load_gold_annotations(path: str | Path) -> list[dict]:
    """Load adjudicated gold JSONL; reject drafts and uncertain labels."""
    path = Path(path)
    rows = []
    seen = set()
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            status = str(_first(row, ("review_status", "status"), "")).lower()
            if status not in {"gold", "adjudicated", "final"}:
                raise ValueError(
                    f"Line {line_no}: review_status must be gold/adjudicated/final; got {status!r}"
                )
            label = str(_first(row, ("gold_label", "label", "risk_label"), "")).lower()
            if label == UNCERTAIN_LABEL:
                raise ValueError(f"Line {line_no}: uncertain labels must be adjudicated or excluded.")
            if label not in VALID_LABELS:
                raise ValueError(f"Line {line_no}: invalid gold label {label!r}.")
            contract_id = _first(row, ("contract_id", "document_id", "doc_id"))
            clause_a = _first(row, ("clause_a_id", "clause1_id", "clause_a"))
            clause_b = _first(row, ("clause_b_id", "clause2_id", "clause_b"))
            pair_id = _first(row, ("pair_id", "annotation_id", "id"))
            if not all((contract_id, clause_a, clause_b, pair_id)):
                raise ValueError(
                    f"Line {line_no}: contract_id, pair_id, clause_a_id and clause_b_id are required."
                )
            if str(clause_a) == str(clause_b):
                raise ValueError(f"Line {line_no}: same-clause pair is invalid.")
            if pair_id in seen:
                raise ValueError(f"Line {line_no}: duplicate pair_id {pair_id!r}.")
            seen.add(pair_id)
            rows.append({
                **row,
                "pair_id": str(pair_id),
                "contract_id": str(contract_id),
                "clause_a_id": str(clause_a),
                "clause_b_id": str(clause_b),
                "gold_label": label,
            })
    if not rows:
        raise ValueError("No adjudicated gold annotations found.")
    return rows


def load_prediction_map(path: str | Path) -> dict[str, dict]:
    """Load per-system predictions JSONL keyed by pair_id."""
    result = {}
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            pair_id = row.get("pair_id")
            system_id = row.get("system_id")
            prediction = str(row.get("prediction", "")).lower()
            if not pair_id or system_id not in {s[0] for s in SYSTEMS}:
                raise ValueError(f"Line {line_no}: pair_id or valid system_id missing.")
            if prediction not in {"risk", "no_risk"}:
                raise ValueError(f"Line {line_no}: prediction must be risk/no_risk.")
            key = (str(system_id), str(pair_id))
            if key in result:
                raise ValueError(f"Line {line_no}: duplicate prediction for {key}.")
            result[key] = row
    return result


def evaluate_ablation(gold_rows: list[dict], prediction_map: dict) -> dict:
    """Calculate per-system binary metrics over exactly the same gold pairs."""
    output = []
    expected_ids = {row["pair_id"] for row in gold_rows}
    for system_id, system_name in SYSTEMS:
        y_true, y_pred = [], []
        missing = []
        for row in gold_rows:
            key = (system_id, row["pair_id"])
            pred = prediction_map.get(key)
            if pred is None:
                missing.append(row["pair_id"])
                continue
            y_true.append(row["gold_label"] == "risk")
            y_pred.append(pred["prediction"] == "risk")
        if missing:
            output.append({
                "id": system_id, "system": system_name, "status": "incomplete_predictions",
                "n_evaluated": len(y_true), "n_gold": len(gold_rows),
                "missing_predictions": missing,
            })
            continue
        metrics = classification_metrics(y_true, y_pred)
        output.append({
            "id": system_id, "system": system_name, "status": "evaluated",
            "n_evaluated": len(y_true), "n_gold": len(gold_rows),
            **metrics,
        })
    return {
        "protocol": "paired_document_grouped_gold_annotation_ablation",
        "gold_pairs": len(gold_rows),
        "documents": len({r["contract_id"] for r in gold_rows}),
        "systems": output,
        "interpretation": (
            "Metrics are valid only for adjudicated human gold labels and complete "
            "predictions for the same pairs. Uncertain labels are excluded only after "
            "documented adjudication or a predeclared exclusion decision."
        ),
    }


def write_document_splits(gold_rows: list[dict], output_dir: str | Path,
                          seed: int = 42, train_fraction: float = 0.70,
                          validation_fraction: float = 0.15) -> dict:
    """Split by contract, never by pair, to prevent document leakage."""
    import random
    if not (0 < train_fraction < 1 and 0 < validation_fraction < 1
            and train_fraction + validation_fraction < 1):
        raise ValueError("Invalid split fractions.")
    documents = sorted({r["contract_id"] for r in gold_rows})
    if len(documents) < 3:
        raise ValueError("At least three distinct contracts are required for grouped splits.")
    rng = random.Random(seed)
    rng.shuffle(documents)
    n = len(documents)
    n_train = max(1, int(n * train_fraction))
    n_val = max(1, int(n * validation_fraction))
    if n_train + n_val >= n:
        n_train = n - 2
        n_val = 1
    assignment = {}
    for doc in documents[:n_train]:
        assignment[doc] = "train"
    for doc in documents[n_train:n_train+n_val]:
        assignment[doc] = "validation"
    for doc in documents[n_train+n_val:]:
        assignment[doc] = "test"
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    counts = defaultdict(int)
    for split in ("train", "validation", "test"):
        subset = [r for r in gold_rows if assignment[r["contract_id"]] == split]
        counts[split] = len(subset)
        with (out / f"{split}.jsonl").open("w", encoding="utf-8") as handle:
            for row in subset:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    manifest = {
        "seed": seed,
        "grouping": "contract_id",
        "documents": {split: sorted(d for d, s in assignment.items() if s == split)
                      for split in ("train", "validation", "test")},
        "pair_counts": dict(counts),
        "document_counts": {split: len(v) for split, v in
                            ((s, [d for d, a in assignment.items() if a == s])
                             for s in ("train", "validation", "test"))},
    }
    (out / "split_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Evaluate ContractGraphAI A1-A5 ablations.")
    parser.add_argument("--gold", required=True, help="Adjudicated gold JSONL.")
    parser.add_argument("--predictions", required=True, help="A1-A5 predictions JSONL.")
    parser.add_argument("--output", default="reports/m7_ablation_results.json")
    parser.add_argument("--make-splits", action="store_true")
    parser.add_argument("--split-dir", default="data/processed/m7_splits")
    args = parser.parse_args()

    gold = load_gold_annotations(args.gold)
    predictions = load_prediction_map(args.predictions)
    results = evaluate_ablation(gold, predictions)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    if args.make_splits:
        print("Document split manifest:")
        print(json.dumps(write_document_splits(gold, args.split_dir), indent=2))


if __name__ == "__main__":
    main()
