import argparse, json, random
from pathlib import Path
from collections import defaultdict
from contractgraph.m6_annotations import validate_annotation_file, write_jsonl
p = argparse.ArgumentParser(description="Create leakage-safe document-level benchmark splits")
p.add_argument("gold_annotations")
p.add_argument("--output-dir", default="data/processed/m6_splits")
p.add_argument("--seed", type=int, default=42)
p.add_argument("--train", type=float, default=.70)
p.add_argument("--validation", type=float, default=.15)
a = p.parse_args()
test_ratio = 1 - a.train - a.validation
if not (0 < a.train < 1 and 0 < a.validation < 1 and 0 < test_ratio < 1):
    raise SystemExit("Split ratios must each be positive and sum to 1")
rows, errors = validate_annotation_file(a.gold_annotations, gold_only=True)
if errors:
    print("Gold annotation validation failed:")
    for e in errors: print("-", e)
    raise SystemExit(1)
by_doc = defaultdict(list)
for row in rows: by_doc[row["document_id"]].append(row)
docs = sorted(by_doc)
if len(docs) < 5:
    raise SystemExit(f"Need at least 5 distinct adjudicated documents; found {len(docs)}")
rng = random.Random(a.seed); rng.shuffle(docs)
n = len(docs)
n_train = max(1, round(n * a.train)); n_val = max(1, round(n * a.validation))
if n_train + n_val >= n: n_train, n_val = n-2, 1
assign = {"train": docs[:n_train], "validation": docs[n_train:n_train+n_val], "test": docs[n_train+n_val:]}
out = Path(a.output_dir); out.mkdir(parents=True, exist_ok=True)
manifest = {"seed": a.seed, "ratios_requested": {"train": a.train, "validation": a.validation, "test": test_ratio},
            "documents": {k: v for k,v in assign.items()}, "records": {}}
for split, split_docs in assign.items():
    split_rows = [r for d in split_docs for r in by_doc[d]]
    write_jsonl(out / f"{split}.jsonl", split_rows)
    manifest["records"][split] = len(split_rows)
sets = [set(assign[k]) for k in assign]
assert not (sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2])
(out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(f"Created document-level splits for {n} documents and {len(rows)} records")
for split in ("train", "validation", "test"):
    print(f"{split}: {len(assign[split])} documents, {manifest['records'][split]} records")
print(f"Manifest: {out / 'manifest.json'}")
