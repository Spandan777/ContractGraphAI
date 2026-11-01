# Human-reviewed cross-clause annotation dataset

## Files
- `annotation_template.jsonl`: one illustrative record to copy and edit. It is deliberately marked `uncertain` and is **not** a gold label.
- `gold_annotations.jsonl`: create this file for completed human-reviewed records. Keep it out of version control if it contains confidential material.

## Unit of annotation
One record represents a pair of clauses from the same contract. Use stable clause IDs from the project's clause segmentation output. Do not infer a conflict merely because two clauses contain different numbers or durations. Compare scope, parties, covered subject matter, trigger, exceptions, definitions and precedence language.

## Allowed labels
- `risk`: a supported cross-clause risk is present.
- `no_risk`: the pair was reviewed and no cross-clause risk was identified.
- `uncertain`: the available text does not support a reliable decision. Keep uncertain cases out of binary scoring until adjudicated.

For `risk`, choose a risk type and severity (`low`, `medium`, `high`) and provide exact evidence text from both clauses. For `no_risk` and `uncertain`, set `risk_type` and `severity` to `not_applicable` and explain the decision in `rationale`.

## Review procedure
1. Analyze the contract as a whole, not just the two snippets.
2. Record exact text in `evidence_a` and `evidence_b`.
3. Explain scope, trigger, exceptions and precedence. Use `None stated` when the contract contains no relevant language.
4. Use `draft` while annotating, `reviewed` after an independent review, and `adjudicated` after disagreements are resolved.
5. Preserve disagreements. Do not silently overwrite one annotator's decision.
6. Split train/validation/test by `document_id`, never by clause pair, to prevent contract-level leakage.

## Validate
From the project root with the virtual environment active:

```powershell
python scripts/validate_annotations.py data/annotations/gold_annotations.jsonl
```

The validator checks JSONL syntax, required fields, allowed labels, evidence presence for risk records and duplicate annotation IDs. It cannot determine whether a legal interpretation is correct. Human/domain-aware review remains essential.

## Privacy
Use public, appropriately licensed, synthetic or explicitly authorized contracts. Do not put confidential contracts into third-party LLM services without authorization. Keep identifying or confidential contract content out of public Git repositories.
