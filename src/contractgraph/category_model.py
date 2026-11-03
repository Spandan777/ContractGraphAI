"""Train/evaluate CUAD clause-category classifier with document-level splits.

This is a clause-category classifier, not a cross-clause conflict classifier.
"""
from __future__ import annotations

import json
from pathlib import Path
from collections import defaultdict

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline


def load_cuad_samples(path: str | Path):
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    articles = payload.get("data", [])
    texts, labels, groups, rows = [], [], [], []
    for article in articles:
        doc_id = article.get("title", "unknown")
        for paragraph in article.get("paragraphs", []):
            context = paragraph.get("context", "")
            for qa in paragraph.get("qas", []):
                question_id = qa.get("id", "")
                category = question_id.split("__")[-1] if "__" in question_id else qa.get("question", "unknown")
                for answer in qa.get("answers", []):
                    answer_text = answer.get("text", "")
                    start = answer.get("answer_start", -1)
                    if not answer_text or not isinstance(start, int):
                        continue
                    end = start + len(answer_text)
                    if context[start:end] != answer_text:
                        continue
                    left, right = max(0, start - 500), min(len(context), end + 500)
                    sample = (
                        "EVIDENCE: " + answer_text + "\nCONTEXT: " + context[left:right]
                    )
                    texts.append(sample)
                    labels.append(category)
                    groups.append(doc_id)
                    rows.append({
                        "document_id": doc_id, "category": category,
                        "answer_text": answer_text, "answer_start": start,
                        "answer_end": end,
                    })
    return texts, labels, groups, rows


def grouped_split(groups, seed=42):
    idx = np.arange(len(groups))
    first = GroupShuffleSplit(n_splits=1, test_size=0.30, random_state=seed)
    train, temp = next(first.split(idx, groups=groups))
    temp_groups = [groups[i] for i in temp]
    second = GroupShuffleSplit(n_splits=1, test_size=0.50, random_state=seed)
    val_local, test_local = next(second.split(temp, groups=temp_groups))
    return train, temp[val_local], temp[test_local]


def train_and_evaluate(cuad_json, output_dir, seed=42):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    texts, labels, groups, rows = load_cuad_samples(cuad_json)
    if len(texts) < 10:
        raise ValueError(f"Only {len(texts)} valid answer spans found.")

    train_idx, val_idx, test_idx = grouped_split(groups, seed)
    train_docs = {groups[i] for i in train_idx}
    val_docs = {groups[i] for i in val_idx}
    test_docs = {groups[i] for i in test_idx}
    assert train_docs.isdisjoint(val_docs | test_docs)
    assert val_docs.isdisjoint(test_docs)

    x_train = [texts[i] for i in train_idx]
    y_train = [labels[i] for i in train_idx]
    x_val = [texts[i] for i in val_idx]
    y_val = [labels[i] for i in val_idx]
    x_test = [texts[i] for i in test_idx]
    y_test = [labels[i] for i in test_idx]

    model = Pipeline([
        ("tfidf", TfidfVectorizer(
            stop_words="english", ngram_range=(1, 2), min_df=2,
            max_features=100000, sublinear_tf=True, strip_accents="unicode"
        )),
        ("classifier", LogisticRegression(
            max_iter=2000, class_weight="balanced", solver="lbfgs",
            random_state=seed
        )),
    ])
    model.fit(x_train, y_train)

    train_categories = set(y_train)
    val_seen = [i for i, y in enumerate(y_val) if y in train_categories]
    test_seen = [i for i, y in enumerate(y_test) if y in train_categories]
    if not test_seen:
        raise ValueError("No test samples belong to categories represented in training.")

    val_pred = model.predict([x_val[i] for i in val_seen]) if val_seen else []
    test_pred = model.predict([x_test[i] for i in test_seen])
    y_val_seen = [y_val[i] for i in val_seen]
    y_test_seen = [y_test[i] for i in test_seen]

    report = classification_report(
        y_test_seen, test_pred, output_dict=True, zero_division=0
    )
    metrics = {
        "task": "CUAD evidence-span clause-category classification",
        "dataset": "CUAD v1",
        "seed": seed,
        "split": "GroupShuffleSplit by contract title",
        "samples_total": len(texts),
        "documents_total": len(set(groups)),
        "categories_total": len(set(labels)),
        "train_samples": len(train_idx),
        "validation_samples": len(val_idx),
        "test_samples": len(test_idx),
        "train_documents": len(train_docs),
        "validation_documents": len(val_docs),
        "test_documents": len(test_docs),
        "validation_seen_category_samples": len(val_seen),
        "validation_unseen_category_samples": len(val_idx) - len(val_seen),
        "test_seen_category_samples": len(test_seen),
        "test_unseen_category_samples_excluded": len(test_idx) - len(test_seen),
        "validation_accuracy_seen_categories": (
            float(accuracy_score(y_val_seen, val_pred)) if val_seen else None
        ),
        "validation_macro_f1_seen_categories": (
            float(f1_score(y_val_seen, val_pred, average="macro", zero_division=0))
            if val_seen else None
        ),
        "test_accuracy_seen_categories": float(accuracy_score(y_test_seen, test_pred)),
        "test_macro_f1_seen_categories": float(
            f1_score(y_test_seen, test_pred, average="macro", zero_division=0)
        ),
        "note": (
            "This evaluates CUAD answer-span category classification only. "
            "It does not evaluate cross-clause conflict detection. Test examples "
            "from categories absent in training are reported but excluded from "
            "closed-set classifier metrics."
        ),
    }

    joblib.dump(model, output_dir / "cuad_category_classifier.joblib")
    (output_dir / "cuad_category_model_metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )
    (output_dir / "cuad_category_classification_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    with (output_dir / "cuad_category_test_predictions.jsonl").open("w", encoding="utf-8") as f:
        for i, pred in zip(test_seen, test_pred):
            f.write(json.dumps({
                "document_id": groups[test_idx[i]],
                "gold_category": y_test[i],
                "predicted_category": str(pred),
                "correct": bool(pred == y_test[i]),
            }, ensure_ascii=False) + "\n")
    return metrics


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--cuad-json", default="data/raw/cuad/CUAD_v1/CUAD_v1.json")
    parser.add_argument("--output-dir", default="models")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    metrics = train_and_evaluate(args.cuad_json, args.output_dir, args.seed)
    print("CUAD CATEGORY MODEL TRAINING COMPLETE")
    print("=" * 45)
    for key, value in metrics.items():
        print(f"{key}: {value}")
    print(f"Model: {Path(args.output_dir) / 'cuad_category_classifier.joblib'}")


if __name__ == "__main__":
    main()
