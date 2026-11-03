from collections import defaultdict
import re

DURATION_RE = re.compile(
    r"\b(\d{1,4}|zero|one|two|three|four|five|six|seven|eight|nine|"
    r"ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|"
    r"eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|"
    r"eighty|ninety)(?:\s*\(\s*(\d{1,4})\s*\))?\s*"
    r"(business\s+days?|calendar\s+days?|days?|weeks?|months?|years?)\b",
    re.I,
)

WORD_VALUES = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30,
    "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90,
}

EXCEPTION_RE = re.compile(
    r"\b(except|excluding|notwithstanding|provided that|unless|"
    r"other than|save for)\b", re.I
)

SURVIVAL_RE = re.compile(
    r"\b(survive|survives|survival|continue in force|"
    r"remain in effect|remain effective)\b", re.I
)




def _duration_values(text, aspect):
    """Extract durations and classify each using its local context."""
    values = []

    for match in DURATION_RE.finditer(text or ""):
        raw_number, parenthesized, unit = match.groups()

        if raw_number.isdigit():
            value = int(raw_number)
        elif parenthesized:
            value = int(parenthesized)
        else:
            value = WORD_VALUES.get(raw_number.lower())

        if value is None:
            continue

        normalized_unit = re.sub(
            r"\s+", " ", unit.lower()
        ).rstrip("s")

        role = _duration_role(
            text, aspect, match.start(), match.end()
        )

        values.append(
            (value, normalized_unit, match.group(0), role)
        )

    return values



def _duration_role(text, aspect, start=None, end=None):
    """Assign a duration role using the nearest preceding contractual cue."""
    text = text or ""

    if start is None:
        local = text
        following = ""
    else:
        local = text[max(0, start - 100):start]
        following = text[end:min(len(text), end + 100)]

    local = local.lower()
    following = following.lower()

    if aspect == "payment":
        if re.search(
            r"\b(within|no later than|due|payable)\b", local
        ) and re.search(
            r"\b(invoice|payment|payable|pay)\b", local
        ):
            return "payment_deadline"
        return None

    if aspect == "termination":
        # Renewal notice durations are often followed by
        # "prior to the renewal date", so inspect both sides.
        if (
            re.search(r"\b(?:notice|notify|notification)\b", local)
            and re.search(r"\b(?:prior to|before)\b", following)
            and re.search(r"\brenewal\b", following)
        ):
            return "renewal_notice"

        cues = [
            (
                "initial_term",
                r"\b(?:initial|original)\s+(?:contract\s+)?"
                r"(?:term|period)\b"
            ),
            (
                "renewal_notice",
                r"\b(?:notice|notify|notification)\b"
                r".{0,120}\b(?:prior to|before)\b"
                r".{0,40}\brenewal\b"
            ),
            (
                "post_termination_survival_or_retention",
                r"\b(?:survive|survival|remain in effect|"
                r"continue in force|retention|maintain records)\b"
            ),
            (
                "renewal_period",
                r"\b(?:renewed|renewal|renewals|renews|renew)\b"
                r".{0,45}\b(?:period|term|successive)\b"
            ),
            (
                "termination_notice",
                r"\b(?:terminate|termination)\b"
                r".{0,45}\b(?:notice|prior)\b"
            ),
        ]

        matches = []

        for role, pattern in cues:
            for match in re.finditer(pattern, local):
                matches.append((match.end(), role))

        if matches:
            return max(matches, key=lambda item: item[0])[1]

        return None

    if aspect == "confidentiality":
        if re.search(
            r"\b(confidential|non-disclosure|disclos)\w*", local
        ) and re.search(
            r"\b(survive|survival|remain in effect|continue in force)\b",
            local,
        ):
            return "confidentiality_survival"

    return None


def _edge_index(graph_edges):
    indexed = defaultdict(list)

    for edge in graph_edges or []:
        source = edge.get("source")
        target = edge.get("target")

        if source and target and source != target:
            indexed[tuple(sorted((source, target)))].append(edge)

    return indexed


def _candidate(
    risk_type, clauses, severity, confidence,
    claim, rationale, signals, graph_relations
):
    ordered = sorted(
        clauses,
        key=lambda c: (c.get("index", 10**9), c["id"])
    )

    return {
        "finding_id": f"M4-{risk_type}-" + "-".join(
            c["id"] for c in ordered
        ),
        "risk_type": risk_type,
        "severity": severity,
        "confidence": round(float(confidence), 3),
        "finding_status": "candidate_for_human_review",
        "claim": claim,
        "rationale": rationale,
        "clauses": [c["id"] for c in ordered],
        "evidence": [c.get("text", "") for c in ordered],
        "signals": signals,
        "graph_relations": sorted(set(graph_relations)),
        "reasoning_method": "deterministic_graph_assisted_heuristics",
        "semantic_conflict_confirmed": False,
    }


def _canonical_risk_type(risk_type):
    aliases = {
        "payment_duration_difference": "payment_duration_mismatch",
        "termination_duration_difference": "termination_duration_mismatch",
        "confidentiality_duration_difference": "confidentiality_duration_mismatch",
        "liability_cap_difference": "liability_cap_scope_review",
    }
    return aliases.get(risk_type, risk_type)


def detect_cross_clause_findings(
    clauses, graph_edges=None, existing_findings=None
):
    """Generate conservative, auditable cross-clause review candidates."""
    by_id = {c["id"]: c for c in clauses}
    edge_index = _edge_index(graph_edges)
    findings = {}

    for pair, edges in edge_index.items():
        first, second = (by_id.get(pair[0]), by_id.get(pair[1]))

        if not first or not second:
            continue

        texts = [
            first.get("text", "") or "",
            second.get("text", "") or "",
        ]

        aspects = (
            set(first.get("aspects", []))
            & set(second.get("aspects", []))
        )

        relations = [
            e.get("relation", "unknown") for e in edges
        ]

        # Compare durations only when their individual contractual roles
        # and units match. Identical clauses are not duration mismatches.
        normalized_texts = [
            re.sub(r"\\s+", " ", t or "").strip().casefold()
            for t in texts
        ]

        if normalized_texts[0] != normalized_texts[1]:
            for aspect in (
                "payment", "termination", "confidentiality"
            ):
                if aspect not in aspects:
                    continue

                left = _duration_values(texts[0], aspect)
                right = _duration_values(texts[1], aspect)

                comparable = [
                    (a, b) for a in left for b in right
                    if (
                        a[3] is not None
                        and a[3] == b[3]
                        and a[1] == b[1]
                        and a[0] != b[0]
                    )
                ]

                if comparable:
                    a, b = comparable[0]
                    risk_type = f"{aspect}_duration_mismatch"

                    findings[(risk_type, pair)] = _candidate(
                        risk_type,
                        [first, second],
                        "medium",
                        0.72,
                        f"The linked {aspect} provisions state different "
                        f"periods for the same identified duration role.",
                        "Review the covered obligations, triggering events, "
                        "applicable scope, precedence and exceptions. "
                        "A duration difference alone does not establish conflict.",
                        {
                            "shared_aspects": sorted(aspects),
                            "duration_role": a[3],
                            "duration_a": a[:3],
                            "duration_b": b[:3],
                        },
                        relations,
                    )

        # Liability cap comparison remains a review candidate.
        if "liability" in aspects:
            cap_re = re.compile(
                r"(?:limited to|shall not exceed|capped at|"
                r"aggregate liability.{0,40}?not exceed)"
                r"\s+([^.;\n]+)",
                re.I,
            )

            caps = [cap_re.search(t) for t in texts]

            if all(caps):
                cap_a = caps[0].group(1).strip()
                cap_b = caps[1].group(1).strip()

                if re.sub(r"\s+", " ", cap_a).lower() != re.sub(
                    r"\s+", " ", cap_b
                ).lower():
                    risk_type = "liability_cap_scope_review"

                    findings[(risk_type, pair)] = _candidate(
                        risk_type,
                        [first, second],
                        "high",
                        0.68,
                        "The linked liability provisions state "
                        "different cap expressions.",
                        "Determine whether the caps apply to the same "
                        "claims, parties, loss types, periods and carve-outs.",
                        {
                            "cap_a": cap_a,
                            "cap_b": cap_b,
                            "shared_aspects": sorted(aspects),
                        },
                        relations,
                    )

        # Generic exception keywords alone are insufficient.
        # Require an explicit cross-clause reference relationship.
        has_explicit_reference = "explicit_reference" in relations
        has_exception_language = any(
            EXCEPTION_RE.search(t) for t in texts
        )

        if (
            has_explicit_reference
            and has_exception_language
            and aspects & {
                "liability", "confidentiality", "payment", "termination"
            }
        ):
            risk_type = "exception_scope_review"

            findings[(risk_type, pair)] = _candidate(
                risk_type,
                [first, second],
                "low",
                0.55,
                "An exception-containing provision explicitly "
                "references another provision in a related risk domain.",
                "Verify the scope of the reference and whether the "
                "exception modifies, overrides or qualifies the other provision.",
                {
                    "shared_aspects": sorted(aspects),
                    "explicit_reference_present": True,
                },
                relations,
            )

        # Survival review remains a candidate, not a conflict conclusion.
        if (
            any(SURVIVAL_RE.search(t) for t in texts)
            and aspects & {
                "confidentiality", "liability", "termination"
            }
        ):
            risk_type = "survival_scope_review"

            findings[(risk_type, pair)] = _candidate(
                risk_type,
                [first, second],
                "low",
                0.52,
                "Survival language is connected to another provision "
                "in a related risk domain.",
                "Verify which obligations survive, their duration, "
                "the triggering event and applicable exceptions.",
                {
                    "shared_aspects": sorted(aspects),
                    "survival_language_present": True,
                },
                relations,
            )

    # Merge equivalent existing rule findings instead of duplicating them.
    for item in existing_findings or []:
        ids = item.get("clauses", [])

        if (
            not isinstance(ids, list)
            or len(ids) < 2
            or any(cid not in by_id for cid in ids)
        ):
            continue

        pair = tuple(sorted(ids[:2]))
        risk_type = _canonical_risk_type(
            item.get("risk_type", "existing_rule_candidate")
        )
        key = (risk_type, pair)

        # Generic exception findings from the old rule engine are
        # intentionally not promoted without explicit reference evidence.
        if risk_type == "exception_scope_review":
            continue

        if key in findings:
            # Keep the graph finding as the primary label when an
            # equivalent A2 liability-cap candidate is injected.
            if risk_type != "liability_cap_scope_review":
                findings[key]['risk_type'] = item.get('risk_type', risk_type)
            findings[key]['signals']['existing_rule_finding'] = item
        else:
            selected = [by_id[cid] for cid in ids[:2]]

            findings[key] = _candidate(
                item.get("risk_type", risk_type),
                selected,
                item.get("severity", "medium"),
                0.60,
                item.get("claim", "Existing rule-based candidate."),
                item.get(
                    "rationale",
                    "Review this rule-based candidate against the source provisions."
                ),
                {"existing_rule_finding": item},
                [
                    e.get("relation", "unknown")
                    for e in edge_index.get(pair, [])
                ],
            )

    return sorted(
        findings.values(),
        key=lambda x: (
            {"high": 0, "medium": 1, "low": 2}.get(
                x["severity"], 3
            ),
            -x["confidence"],
            x["finding_id"],
        ),
    )
