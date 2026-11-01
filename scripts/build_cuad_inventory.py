#!/usr/bin/env python3
"""Create CUAD contract inventory and deterministic workflow pilot."""
from __future__ import annotations
import argparse, csv, json, random, re, unicodedata
from pathlib import Path
from collections import Counter, defaultdict

def clean(value):
    if value is None:
        return ""
    value = str(value).strip()
    return "" if value.lower() in {"nan", "none", "null"} else value

def normalize_filename(name):
    value = unicodedata.normalize("NFKC", clean(name))
    value = value.rstrip(" \\t\\r\\n\\\"'")
    value = re.sub(r"\\.pdf$", "", value, flags=re.IGNORECASE)
    value = value.casefold()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def get_category_pairs(headers):
    pairs = []
    i = 1
    while i + 1 < len(headers):
        context, answer = headers[i], headers[i + 1]
        if answer.lower().replace(" ", "").endswith("-answer"):
            pairs.append((context, context, answer))
            i += 2
        else:
            raise ValueError(
                f"Unexpected master CSV layout at columns {context!r}, {answer!r}"
            )
    if i != len(headers):
        raise ValueError("Master CSV has an unmatched final column.")
    return pairs

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--pilot-size", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    cuad = root / "data/raw/cuad/CUAD_v1"
    csv_path, json_path = cuad / "master_clauses.csv", cuad / "CUAD_v1.json"
    pdf_root = cuad / "full_contract_pdf"
    for p in (csv_path, json_path, pdf_root):
        if not p.exists():
            raise FileNotFoundError(f"Required CUAD path not found: {p}")

    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = list(reader)
    pairs = get_category_pairs(headers)

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    json_records = {
        clean(r.get("title")).casefold(): r
        for r in payload.get("data", []) if clean(r.get("title"))
    }

    json_normalized_index = defaultdict(list)
    for json_record in payload.get("data", []):
        json_title = clean(json_record.get("title"))
        if json_title:
            json_normalized_index[normalize_filename(json_title)].append(json_record)

    pdf_paths = sorted(pdf_root.rglob("*.pdf"))
    exact_pdf_index = defaultdict(list)
    normalized_pdf_index = defaultdict(list)
    actual_pdf_names = defaultdict(list)

    for pdf in pdf_paths:
        exact_pdf_index[pdf.name.casefold()].append(pdf)
        normalized_pdf_index[normalize_filename(pdf.name)].append(pdf)
        actual_pdf_names[pdf.name].append(pdf)

    manual_aliases = {
        "HarpoonTherapeuticsInc_20200312_10-K_EX-10.18_12051356_EX-10.18_Development Agreement.PDF":
        "HarpoonTherapeuticsInc_20200312_10-K_EX-10.18_12051356_EX-10.18_Development Agreement_Option Agreement.pdf",
        "WOMENSGOLFUNLIMITEDINC_03_29_2000-EX-10.13-ENDORSEMENT AGREEMENT - Intellectual Property Rights                 Confidentiality and Non-Use Obligations Agreement.pdf":
        "WOMENSGOLFUNLIMITEDINC_2000_EX10_13_IPR_CONFIDENTIALITY.pdf"
    }

    pdfs = pdf_paths

    inventory, coverage, context_coverage = [], Counter(), Counter()
    missing_pdf, missing_json = [], []
    pdf_audit = []

    for row_no, row in enumerate(rows, start=2):
        filename = clean(row.get("Filename"))
        title = Path(filename).stem
        record = json_records.get(title.casefold())
        json_match_method = "exact" if record else "unmatched"

        if record is None:
            candidates = json_normalized_index.get(
                normalize_filename(title), []
            )
            if len(candidates) == 1:
                record = candidates[0]
                json_match_method = "normalized_unique"
            elif len(candidates) > 1:
                json_match_method = "normalized_ambiguous"

        expected_pdf = Path(filename).name
        matched_pdf = None
        pdf_match_method = "unmatched"

        alias = manual_aliases.get(expected_pdf)
        alias_matches = actual_pdf_names.get(alias, []) if alias else []

        if alias:
            if len(alias_matches) == 1:
                matched_pdf = alias_matches[0]
                pdf_match_method = "manual_reviewed_alias"
            elif len(alias_matches) > 1:
                pdf_match_method = "manual_alias_ambiguous"
        else:
            exact_matches = exact_pdf_index.get(expected_pdf.casefold(), [])

            if len(exact_matches) == 1:
                matched_pdf = exact_matches[0]
                pdf_match_method = "exact_case_insensitive"
            elif len(exact_matches) > 1:
                pdf_match_method = "exact_ambiguous"
            else:
                normalized_matches = normalized_pdf_index.get(
                    normalize_filename(expected_pdf), []
                )
                if len(normalized_matches) == 1:
                    matched_pdf = normalized_matches[0]
                    pdf_match_method = "normalized_unique"
                elif len(normalized_matches) > 1:
                    pdf_match_method = "normalized_ambiguous"

        pdf_path = (
            matched_pdf.relative_to(root).as_posix()
            if matched_pdf else ""
        )

        pdf_audit.append({
            "row_number": row_no,
            "expected_pdf_filename": expected_pdf,
            "matched_pdf_filename": matched_pdf.name if matched_pdf else "",
            "matched_pdf_path": pdf_path,
            "match_method": pdf_match_method,
            "match_status": (
                "matched" if matched_pdf else
                "ambiguous" if "ambiguous" in pdf_match_method else
                "unmatched"
            )
        })

        present = []
        contexts = answers = 0
        for category, context_col, answer_col in pairs:
            context, answer = clean(row.get(context_col)), clean(row.get(answer_col))
            if context or answer:
                present.append(category)
                coverage[category] += 1
            if context:
                contexts += 1
                context_coverage[category] += 1
            if answer:
                answers += 1
        if not pdf_path:
            missing_pdf.append(filename)
        if record is None:
            missing_json.append(title)
        inventory.append({
            "row_number": row_no, "filename": filename, "title": title,
            "pdf_path": pdf_path,
            "pdf_match_method": pdf_match_method,
            "json_record_found": bool(record),
            "json_match_method": json_match_method,
            "json_paragraph_count": len(record.get("paragraphs", [])) if record else 0,
            "json_qa_count": sum(len(p.get("qas", [])) for p in record.get("paragraphs", [])) if record else 0,
            "categories_with_any_annotation": len(present),
            "categories_with_context": contexts, "categories_with_answer": answers,
            "present_categories": "|".join(present)
        })

    out = root / "data/processed"
    out.mkdir(parents=True, exist_ok=True)
    inv_path = out / "cuad_contract_inventory.csv"
    with inv_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(inventory[0].keys()))
        w.writeheader(); w.writerows(inventory)

    cov_path = out / "cuad_category_coverage.csv"
    with cov_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["category", "contracts_with_context_or_answer", "contracts_with_context"])
        for category, _, _ in pairs:
            w.writerow([category, coverage[category], context_coverage[category]])

    n = min(max(args.pilot_size, 0), len(inventory))
    pilot = random.Random(args.seed).sample(inventory, n) if n else []
    pilot_path = out / f"cuad_pilot_{n}.csv"
    fields = ["filename", "title", "pdf_path", "pdf_match_method",
              "json_record_found", "json_match_method",
              "categories_with_any_annotation", "categories_with_context",
              "categories_with_answer", "present_categories"]
    with pilot_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for item in pilot:
            w.writerow({k: item[k] for k in fields})

    audit_path = out / "cuad_pdf_match_audit.csv"
    with audit_path.open("w", encoding="utf-8-sig", newline="") as f:
        audit_fields = [
            "row_number", "expected_pdf_filename", "matched_pdf_filename",
            "matched_pdf_path", "match_method", "match_status"
        ]
        writer = csv.DictWriter(f, fieldnames=audit_fields)
        writer.writeheader()
        writer.writerows(pdf_audit)

    summary = {
        "dataset": "CUAD v1", "csv_contract_records": len(rows),
        "csv_columns": len(headers), "category_count": len(pairs),
        "json_contract_records": len(json_records), "pdf_files_found": len(pdf_paths),
        "records_missing_pdf": len(missing_pdf),
        "records_missing_json_match": len(missing_json),
        "json_matches_exact": sum(
            x["json_match_method"] == "exact" for x in inventory
        ),
        "json_matches_normalized": sum(
            x["json_match_method"] == "normalized_unique" for x in inventory
        ),
        "json_ambiguous_matches": sum(
            x["json_match_method"] == "normalized_ambiguous" for x in inventory
        ),
        "pdf_matches_exact": sum(
            x["match_method"] == "exact_case_insensitive" for x in pdf_audit
        ),
        "pdf_matches_normalized": sum(
            x["match_method"] == "normalized_unique" for x in pdf_audit
        ),
        "pdf_matches_manual_alias": sum(
            x["match_method"] == "manual_reviewed_alias" for x in pdf_audit
        ),
        "pdf_ambiguous_matches": sum(
            x["match_status"] == "ambiguous" for x in pdf_audit
        ),
        "pilot_size": n, "pilot_seed": args.seed,
        "pilot_note": "Workflow pilot only; not a statistically representative evaluation sample.",
        "outputs": [
            p.relative_to(root).as_posix()
            for p in (inv_path, cov_path, pilot_path, audit_path)
        ],
        "missing_pdf_filenames": missing_pdf, "missing_json_titles": missing_json
    }
    (out / "cuad_inventory_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"CUAD inventory created: {len(rows)} contracts")
    print(f"Category columns identified: {len(pairs)}")
    print(
        f"PDFs matched: {len(rows)-len(missing_pdf)} / {len(rows)} "
        f"(exact={summary['pdf_matches_exact']}, "
        f"normalized={summary['pdf_matches_normalized']}, "
        f"manual_alias={summary['pdf_matches_manual_alias']})"
    )
    print(f"PDF ambiguous matches: {summary['pdf_ambiguous_matches']}")
    print(
        f"JSON records matched: {len(rows)-len(missing_json)} / {len(rows)} "
        f"(exact={summary['json_matches_exact']}, "
        f"normalized={summary['json_matches_normalized']})"
    )
    print(f"JSON ambiguous matches: {summary['json_ambiguous_matches']}")
    print(f"PDF audit: {audit_path}")
    print(f"Pilot selected: {n} (seed={args.seed})")
    print(f"Output directory: {out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
