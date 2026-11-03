import re
import networkx as nx

REFERENCE_PATTERNS = [
    re.compile(
        r"\b(?:as set out|as described|subject to|pursuant to|under|"
        r"in accordance with|refer to|see)\s+(?:section|clause|article|"
        r"paragraph|schedule|exhibit)\s+([\w.-]+)",
        re.I,
    ),
    re.compile(
        r"\b(?:section|clause|article|paragraph|schedule|exhibit)\s+"
        r"([\w.-]+)",
        re.I,
    ),
]

RISK_ASPECTS = {"payment", "termination", "liability", "confidentiality"}

CONDITION_RE = re.compile(
    r"\b(if|when|upon|after|before|subject to|provided that|"
    r"following|unless)\b", re.I
)
EXCEPTION_RE = re.compile(
    r"\b(except|excluding|notwithstanding|provided that|"
    r"unless|other than|save for)\b", re.I
)
SURVIVAL_RE = re.compile(
    r"\b(survive|survives|survival|continue in force|"
    r"remain in effect|remain effective)\b", re.I
)
OBLIGATION_RE = re.compile(
    r"\b(shall|must|required to|undertakes|agrees to|"
    r"is obligated to)\b", re.I
)


def _text(clause):
    return clause.get("text", "") or ""


def _aspects(clause):
    return set(clause.get("aspects", []))


def _add_edge(graph, source, target, relation, reason,
              method="keyword_heuristic", confidence=0.5):
    if source == target:
        return
    graph.add_edge(
        source, target,
        relation=relation,
        reason=reason,
        method=method,
        confidence=confidence,
    )


def _resolve_reference(reference, clauses):
    reference = reference.lower().strip().rstrip(".")
    for clause in clauses:
        clause_id = str(clause.get("id", "")).lower()
        title = str(clause.get("title", "")).lower()
        if clause_id == reference:
            return clause["id"]
        patterns = [
            rf"\b(?:section|clause|article|paragraph|schedule|exhibit)"
            rf"\s+{re.escape(reference)}(?:\b|[.):])",
            rf"^\s*{re.escape(reference)}(?:\s|[.):]|$)",
        ]
        if any(re.search(pattern, title, re.I) for pattern in patterns):
            return clause["id"]
    return None


def build_dependency_graph(clauses):
    """Build an auditable heuristic clause graph, not legal conclusions."""
    graph = nx.MultiDiGraph()

    for clause in clauses:
        graph.add_node(
            clause["id"],
            title=clause.get("title", ""),
            aspects=clause.get("aspects", []),
            text=_text(clause),
            index=clause.get("index"),
            attributes={
                key: value for key, value in clause.items()
                if key not in {"id", "title", "text"}
            },
        )

    # Resolve explicit references and reference-based dependencies.
    for clause in clauses:
        source = clause["id"]
        for pattern in REFERENCE_PATTERNS:
            for match in pattern.finditer(_text(clause)):
                reference = match.group(1)
                target = _resolve_reference(reference, clauses)
                if target is not None and target != source:
                    _add_edge(
                        graph, source, target, "explicit_reference",
                        f"Explicit reference to {reference}",
                        method="regex_reference_resolution",
                        confidence=0.90,
                    )
                    _add_edge(
                        graph, source, target, "obligation_dependency",
                        "A clause explicitly refers to another provision.",
                        method="reference_based_candidate",
                        confidence=0.75,
                    )

    for i, first in enumerate(clauses):
        for second in clauses[i + 1:]:
            first_id, second_id = first["id"], second["id"]
            first_text, second_text = _text(first), _text(second)
            first_aspects, second_aspects = _aspects(first), _aspects(second)
            shared = first_aspects & second_aspects

            if shared:
                _add_edge(
                    graph, first_id, second_id, "shared_aspect",
                    "Shared tags: " + ", ".join(sorted(shared)),
                    confidence=0.55,
                )

            risk_overlap = shared & RISK_ASPECTS
            if risk_overlap:
                _add_edge(
                    graph, first_id, second_id, "potential_conflict",
                    "Shared risk domain; compare scope, triggers, precedence and exceptions.",
                    method="candidate_generation",
                    confidence=0.35,
                )

            first_exception = "exception" in first_aspects or bool(EXCEPTION_RE.search(first_text))
            second_exception = "exception" in second_aspects or bool(EXCEPTION_RE.search(second_text))

            if first_exception and (second_aspects & RISK_ASPECTS):
                _add_edge(
                    graph, first_id, second_id, "exception_to",
                    "Exception language may qualify the related risk provision.",
                    method="exception_keyword_heuristic",
                    confidence=0.50,
                )
            if second_exception and (first_aspects & RISK_ASPECTS):
                _add_edge(
                    graph, second_id, first_id, "exception_to",
                    "Exception language may qualify the related risk provision.",
                    method="exception_keyword_heuristic",
                    confidence=0.50,
                )

            first_survival = bool(SURVIVAL_RE.search(first_text))
            second_survival = bool(SURVIVAL_RE.search(second_text))
            if first_survival and second_aspects:
                _add_edge(
                    graph, first_id, second_id, "temporal_dependency",
                    "Survival language may govern the duration of a related provision.",
                    method="survival_language_heuristic",
                    confidence=0.55,
                )
            if second_survival and first_aspects:
                _add_edge(
                    graph, second_id, first_id, "temporal_dependency",
                    "Survival language may govern the duration of a related provision.",
                    method="survival_language_heuristic",
                    confidence=0.55,
                )

            first_conditional = bool(CONDITION_RE.search(first_text) and OBLIGATION_RE.search(first_text))
            second_conditional = bool(CONDITION_RE.search(second_text) and OBLIGATION_RE.search(second_text))
            if first_conditional and shared:
                _add_edge(
                    graph, first_id, second_id, "conditional_dependency",
                    "Conditional obligation shares an aspect with another clause.",
                    method="condition_keyword_heuristic",
                    confidence=0.40,
                )
            if second_conditional and shared:
                _add_edge(
                    graph, second_id, first_id, "conditional_dependency",
                    "Conditional obligation shares an aspect with another clause.",
                    method="condition_keyword_heuristic",
                    confidence=0.40,
                )

    return graph


def edges_as_dicts(graph):
    return [
        {"source": source, "target": target, **attributes}
        for source, target, attributes in graph.edges(data=True)
    ]
