from __future__ import annotations
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.contractgraph.annotation_schema import validate_jsonl


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate ContractGraph AI annotation JSONL")
    parser.add_argument("path", nargs="?", default="data/annotations/gold_annotations.jsonl")
    args = parser.parse_args()
    count, errors = validate_jsonl(args.path)
    if errors:
        print(f"Validation failed: {len(errors)} issue(s), {count} record(s) read.")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Validation successful: {count} annotation record(s).")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
