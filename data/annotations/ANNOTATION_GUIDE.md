# CUAD Cross-Clause Annotation Guide

This is a review queue, not a gold-labelled dataset.
All labels are intentionally blank.

## Unit of annotation

Review both CUAD evidence spans and their full source paragraph contexts.
Answer spans may not represent complete contractual clauses.
Inspect the surrounding contract before assigning a label.

## Labels

- risk: Actual incompatible obligations, rights, restrictions,
  exceptions, triggers, durations, remedies or precedence problems.
- no_risk: Provisions are compatible, address distinct subjects,
  or expressly reconcile their interaction.
- uncertain: Available context is insufficient or requires
  interpretation beyond this annotation protocol.

## Required review

Record rationale, risk type and severity for risk findings.
Assess scope, trigger, exceptions and precedence.
Cite exact source text.

Do not infer a conflict merely because two durations or categories differ.

## Quality controls

- Preserve uncertain labels when evidence is insufficient.
- Independently review a subset with a second annotator.
- Adjudicate disagreements.
- Split datasets by document_id, never by candidate pair.
- CUAD categories are not cross-clause conflict labels.
- Never use draft or AI-assisted labels as gold evaluation data.
