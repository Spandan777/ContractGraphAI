# M6 Human Annotation Protocol

## Unit and context
The annotation unit is a candidate pair of CUAD evidence spans from one contract.
CUAD answer spans are not guaranteed to represent complete clauses. Read both full
paragraph contexts and inspect surrounding contract text when available. Record whether
the pair concerns the same parties, subject matter, scope, trigger, time period, remedy,
and precedence hierarchy.

## Labels
- **risk**: the provisions create an actual incompatible obligation, right, restriction,
  exception, trigger, duration, remedy, or precedence problem.
- **no_risk**: provisions are compatible, govern distinct scopes, or expressly reconcile
  their interaction.
- **uncertain**: evidence is insufficient or the interaction cannot be resolved under
  this protocol. Do not force a binary decision.

## Decision checklist
1. Are both passages operative contractual language?
2. Do they concern the same parties and subject matter?
3. Do their scopes overlap?
4. Are the triggers and conditions compatible?
5. Do exceptions qualify or reconcile the provisions?
6. Is there an express precedence or order-of-control clause?
7. Is there a genuine incompatibility after considering the above?

A difference in clause category, wording, amount, or duration alone is not sufficient.

## Required fields
For each pair, record the label, rationale, risk type and severity if risk, scope,
trigger, exception, precedence analysis, annotator, and review status. For risk labels,
quote exact evidence from both provisions. For no_risk/uncertain, set risk_type and
severity to `not_applicable` and explain why.

## Review and adjudication
Two annotators should label independently before discussing disagreements. Report
raw agreement and Cohen's kappa on shared candidate IDs. A third reviewer or documented
consensus process adjudicates disagreements. Gold benchmark records must have
`review_status=adjudicated` and identify the adjudicator. Preserve original reviewer
files; never overwrite them with adjudicated labels.

## Sampling and leakage
Keep all pairs from a contract in exactly one split. Use document-level train,
validation, and test splits. Do not tune thresholds or rules on the test set. Because
the current pilot queue contains only 37 pairs, report counts and uncertainty and avoid
claiming broad generalization.

## Provenance
Keep AI-generated candidate findings, AI-assisted annotation drafts, independent human
annotations, adjudicated gold labels, and system predictions in separate files.
Only adjudicated human labels are eligible as gold evaluation targets.
