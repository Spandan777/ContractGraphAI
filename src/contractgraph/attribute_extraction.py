"""Deterministic structured extraction of contract clause attributes.

These extractors are transparent heuristics, not trained legal models.
They produce candidate attributes for downstream graph reasoning and review.
"""
from __future__ import annotations

import re
from typing import Any

NUMBER_WORDS = (
    "twenty[- ]?one|twenty[- ]?two|twenty[- ]?three|twenty[- ]?four|"
    "twenty[- ]?five|twenty[- ]?six|twenty[- ]?seven|twenty[- ]?eight|"
    "twenty[- ]?nine|thirty|forty|fifty|sixty|seventy|eighty|ninety|"
    "nineteen|eighteen|seventeen|sixteen|fifteen|fourteen|thirteen|"
    "twelve|eleven|ten|nine|eight|seven|six|five|four|three|two|one|zero"
)

DURATION_RE = re.compile(
    rf"\b(?:(?P<value>\d{{1,4}})|"
    rf"(?P<word>{NUMBER_WORDS})(?:\s*\(\s*(?P<paren>\d{{1,4}})\s*\))?)"
    rf"\s*(?P<unit>business\s+days?|calendar\s+days?|days?|weeks?|months?|years?)\b",
    re.I,
)

WORD_VALUES = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}
MONEY_RE = re.compile(
    r"(?P<currency>USD|EUR|GBP|INR|US\$|C\$|A\$|\$|€|£|₹)\s*"
    r"(?P<amount>\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)",
    re.I,
)
PERCENT_RE = re.compile(r"\b(?P<value>\d+(?:\.\d+)?)\s*%")
DATE_RE = re.compile(
    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{1,2},?\s+\d{4}\b|\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
    re.I,
)
REFERENCE_RE = re.compile(
    r"\b(?:section|clause|article|paragraph|schedule|exhibit)\s+"
    r"(?P<reference>[\w.-]+(?:\([a-z0-9]+\))?)",
    re.I,
)
PARTY_RE = re.compile(
    r"\b(the\s+(?:customer|client|company|supplier|vendor|provider|licensor|licensee|"
    r"disclosing party|receiving party|buyer|seller|contractor|subcontractor))\b",
    re.I,
)
OBLIGATION_RE = re.compile(
    r"\b(?P<modal>shall|must|will|may not|shall not|must not|is required to|"
    r"agrees to|undertakes to)\b(?P<action>[^.;\n]{0,240})",
    re.I,
)
TRIGGER_RE = re.compile(
    r"\b(if|when|upon|following|after|before|in the event that|provided that|"
    r"subject to|to the extent that)\b(?P<condition>[^.;\n]{0,240})",
    re.I,
)
EXCEPTION_RE = re.compile(
    r"\b(except(?: that| as)?|excluding|notwithstanding|provided however|"
    r"unless|other than|does not apply to|shall not apply to)\b"
    r"(?P<exception>[^.;\n]{0,300})",
    re.I,
)
SURVIVAL_RE = re.compile(
    r"\b(surviv(?:e|es|al|ing)|continue[s]? after termination|"
    r"remain in effect after termination|following expiration)\b"
    r"(?P<context>[^.;\n]{0,220})",
    re.I,
)
ASPECT_PATTERNS = {
    "payment": r"\b(payment|invoice|fee|payable|compensation|remittance|price)\b",
    "termination": r"\b(termination|terminate|notice period|expiry|expiration)\b",
    "liability": r"\b(liability|liable|damages|indemnif|limitation of liability)\b",
    "confidentiality": r"\b(confidential|non-disclosure|disclose|proprietary information)\b",
    "obligation": r"\b(shall|must|required to|undertakes|agrees to)\b",
    "exception": r"\b(except|excluding|notwithstanding|provided that|unless|carve.?out)\b",
    "governing_law": r"\b(governing law|jurisdiction|venue|courts of)\b",
    "data_protection": r"\b(personal data|data protection|privacy|gdpr|security incident)\b",
    "intellectual_property": r"\b(intellectual property|work product|ownership|license|licence|copyright)\b",
    "force_majeure": r"\b(force majeure|unforeseeable event|act of god)\b",
}

def _matches(pattern: re.Pattern, text: str, group: str | None = None) -> list[str]:
    values = []
    for match in pattern.finditer(text):
        value = match.group(group) if group else match.group(0)
        values.append(re.sub(r"\s+", " ", value).strip())
    return values

def extract_clause_attributes(text: str) -> dict[str, Any]:
    """Extract auditable candidate attributes from a clause string."""
    if not isinstance(text, str):
        text = ""
    durations = []
    for m in DURATION_RE.finditer(text):
        unit = re.sub(r"\s+", " ", m.group("unit").lower())
        if m.group("value"):
            value = int(m.group("value"))
        elif m.group("paren"):
            value = int(m.group("paren"))
        else:
            word = m.group("word").lower().replace("-", " ")
            parts = word.split()
            value = sum(WORD_VALUES[p] for p in parts)

        durations.append({
            "value": value,
            "unit": unit.rstrip("s"),
            "raw": m.group(0),
            "start": m.start(),
            "end": m.end(),
        })

    monetary_values = []
    for m in MONEY_RE.finditer(text):
        monetary_values.append({
            "currency": m.group("currency").upper(),
            "amount": m.group("amount").replace(",", ""),
            "raw": m.group(0),
            "start": m.start(),
            "end": m.end(),
        })

    percentages = [
        {"value": float(m.group("value")), "raw": m.group(0),
         "start": m.start(), "end": m.end()}
        for m in PERCENT_RE.finditer(text)
    ]

    return {
        "aspects": [name for name, pattern in ASPECT_PATTERNS.items()
                    if re.search(pattern, text, re.I)],
        "durations": durations,
        "monetary_values": monetary_values,
        "percentages": percentages,
        "dates": _matches(DATE_RE, text),
        "references": [x.rstrip(".") for x in _matches(REFERENCE_RE, text, "reference")],
        "parties": sorted(set(_matches(PARTY_RE, text))),
        "obligations": [
            {"modal": m.group("modal"), "action": m.group("action").strip(),
             "start": m.start(), "end": m.end()}
            for m in OBLIGATION_RE.finditer(text)
        ],
        "triggers": [
            {"keyword": m.group(1), "condition": m.group("condition").strip(),
             "start": m.start(), "end": m.end()}
            for m in TRIGGER_RE.finditer(text)
        ],
        "exceptions": [
            {"keyword": m.group(1), "text": m.group("exception").strip(),
             "start": m.start(), "end": m.end()}
            for m in EXCEPTION_RE.finditer(text)
        ],
        "survival_terms": [
            {"keyword": m.group(1), "context": m.group("context").strip(),
             "start": m.start(), "end": m.end()}
            for m in SURVIVAL_RE.finditer(text)
        ],
        "has_exception": bool(EXCEPTION_RE.search(text)),
        "has_survival_language": bool(SURVIVAL_RE.search(text)),
        "extraction_method": "transparent_regex_heuristics",
        "semantic_validation": False,
    }
