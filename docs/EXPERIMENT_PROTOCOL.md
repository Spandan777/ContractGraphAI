# Experiment protocol

Research question: Can graph-based cross-clause reasoning improve risk detection compared with independent retrieval and clause-level analysis?

Ablations:
A1 independent retrieval; A2 retrieval + aspect tagging; A3 retrieval + graph candidates; A4 graph + cross-clause rules; A5 full pipeline + evidence traceability.

Metrics: precision, recall, F1, Recall@K, evidence traceability accuracy, per-risk-type results and false-positive analysis.

Split at contract level to prevent leakage. Annotate clause pairs with risk presence/type/severity, rationale, scope, trigger, precedence, exceptions and adjudication status. Use the same held-out contracts for every ablation.

A domain-aware human reviewer must adjudicate whether apparent differences are actual conflicts, scoped variations, exceptions or ambiguous cases. Report dataset counts, split strategy, annotation agreement, software/model versions, prompts and failure cases. Never report synthetic-demo output as benchmark performance.
