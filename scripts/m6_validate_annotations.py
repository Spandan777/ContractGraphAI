import argparse
from contractgraph.m6_annotations import validate_annotation_file
p = argparse.ArgumentParser(description="Validate completed M6 human annotations")
p.add_argument("path")
p.add_argument("--gold-only", action="store_true", help="Require every record to be adjudicated")
a = p.parse_args()
rows, errors = validate_annotation_file(a.path, gold_only=a.gold_only)
if errors:
    print(f"Validation FAILED: {len(errors)} issue(s), {len(rows)} record(s)")
    for e in errors: print("-", e)
    raise SystemExit(1)
print(f"Validation successful: {len(rows)} human-reviewed record(s)")
if a.gold_only: print("Gold status: all records adjudicated")
