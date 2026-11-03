import argparse, json
from pathlib import Path
from contractgraph.m6_annotations import agreement_from_files
p = argparse.ArgumentParser(description="Compute inter-annotator agreement")
p.add_argument("annotator_a")
p.add_argument("annotator_b")
p.add_argument("--output", default="data/processed/m6_agreement.json")
a = p.parse_args()
r = agreement_from_files(a.annotator_a, a.annotator_b)
Path(a.output).parent.mkdir(parents=True, exist_ok=True)
Path(a.output).write_text(json.dumps(r, indent=2), encoding="utf-8")
print(f"Shared pairs: {r['n']}")
print(f"Observed agreement: {r['observed_agreement']:.4f}")
print(f"Cohen's kappa: {r['cohen_kappa']:.4f}")
print(f"Agreement report: {a.output}")
