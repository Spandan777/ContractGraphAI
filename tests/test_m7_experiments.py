import json
import pytest

from contractgraph.experiment_runner import (
    load_gold_annotations, evaluate_ablation, write_document_splits, SYSTEMS
)


def _gold(tmp_path, labels=None, status="gold"):
    labels = labels or ["risk", "no_risk", "risk", "no_risk", "risk", "no_risk"]
    path = tmp_path / "gold.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for i, label in enumerate(labels):
            f.write(json.dumps({
                "pair_id": f"P{i}", "contract_id": f"D{i//2}",
                "clause_a_id": f"C{i}A", "clause_b_id": f"C{i}B",
                "gold_label": label, "review_status": status
            }) + "\n")
    return path


def test_load_adjudicated_gold(tmp_path):
    rows = load_gold_annotations(_gold(tmp_path))
    assert len(rows) == 6
    assert len({r["contract_id"] for r in rows}) == 3


def test_reject_draft_annotations(tmp_path):
    with pytest.raises(ValueError, match="review_status"):
        load_gold_annotations(_gold(tmp_path, status="draft"))


def test_reject_uncertain_labels(tmp_path):
    with pytest.raises(ValueError, match="uncertain"):
        load_gold_annotations(_gold(tmp_path, labels=["uncertain"] * 6))


def test_reject_duplicate_pairs(tmp_path):
    path = tmp_path / "duplicate.jsonl"
    row = {"pair_id":"P","contract_id":"D","clause_a_id":"A",
           "clause_b_id":"B","gold_label":"risk","review_status":"gold"}
    path.write_text(json.dumps(row)+"\n"+json.dumps(row)+"\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        load_gold_annotations(path)


def test_evaluate_all_five_systems(tmp_path):
    gold = load_gold_annotations(_gold(tmp_path))
    preds = {}
    for sid, _ in SYSTEMS:
        for row in gold:
            preds[(sid, row["pair_id"])] = {
                "prediction": row["gold_label"]
            }
    result = evaluate_ablation(gold, preds)
    assert len(result["systems"]) == 5
    assert all(x["status"] == "evaluated" for x in result["systems"])
    assert all(x["f1"] == 1.0 for x in result["systems"])


def test_missing_prediction_is_not_silently_scored(tmp_path):
    gold = load_gold_annotations(_gold(tmp_path))
    result = evaluate_ablation(gold, {})
    assert all(x["status"] == "incomplete_predictions" for x in result["systems"])


def test_document_grouped_splits_have_no_leakage(tmp_path):
    gold = load_gold_annotations(_gold(tmp_path))
    manifest = write_document_splits(gold, tmp_path / "splits", seed=42)
    sets = [set(manifest["documents"][s]) for s in ("train", "validation", "test")]
    assert not (sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2])
    assert len(set.union(*sets)) == 3
