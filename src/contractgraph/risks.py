import re
from itertools import combinations


_WORD_VALUES = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}

_WORD_TOKEN = (
    r"zero|one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|"
    r"seventeen|eighteen|nineteen|twenty|thirty|forty|"
    r"fifty|sixty|seventy|eighty|ninety|hundred|thousand"
)

_WORD_NUMBER = (
    rf"(?:{_WORD_TOKEN})"
    rf"(?:(?:[ -]+and)?[ -]+(?:{_WORD_TOKEN}))*"
)

DURATION = re.compile(
    rf"\b(?P<number>\d{{1,4}}|{_WORD_NUMBER})\s*"
    r"(?P<unit>business\s+days?|calendar\s+days?|days?|weeks?|months?|years?)\b",
    re.I,
)


def _words_to_int(value):
    total = 0
    current = 0

    tokens = re.split(r"[ -]+", value.lower().replace(" and ", " "))

    for token in tokens:
        if token == "hundred":
            current = max(current, 1) * 100
        elif token == "thousand":
            total += max(current, 1) * 1000
            current = 0
        elif token in _WORD_VALUES:
            current += _WORD_VALUES[token]

    return total + current


def _normalize_unit(unit):
    unit = re.sub(r"\s+", " ", unit.lower()).strip()

    if unit.endswith("s"):
        unit = unit[:-1]

    unit = unit.replace("business day", "business_day")
    unit = unit.replace("calendar day", "calendar_day")

    return unit


def _dur(text):
    values = []

    for match in DURATION.finditer(text or ""):
        raw_number = match.group("number")

        number = (
            int(raw_number)
            if raw_number.isdigit()
            else _words_to_int(raw_number)
        )

        unit = _normalize_unit(match.group("unit"))

        values.append({
            "value": number,
            "unit": unit,
            "start": match.start(),
            "end": match.end(),
            "text": match.group(0),
        })

    return values


def _normalize_clause(text):
    return re.sub(r"\s+", " ", (text or "")).strip().casefold()


def _duration_role(text, aspect):
    text = text or ""

    if aspect == "termination":

        if re.search(r"\b(cure|remedy|remedial period)\b", text, re.I):
            return "cure_period"

        if re.search(
            r"\b(transition[- ]out|transition period|wind[- ]down period)\b",
            text, re.I
        ):
            return "transition_period"

        if re.search(
            r"\b(non[- ]renewal|nonrenewal|not\s+(?:to\s+)?renew|"
            r"intention\s+not\s+to\s+renew)\b",
            text, re.I
        ):
            return "non_renewal_notice"

        if (
            re.search(r"\b(renew|renewal|renewed)\b", text, re.I)
            and re.search(
                r"\b(notice|notify|written notice|choice to renew|option to renew)\b",
                text, re.I
            )
        ):
            return "renewal_exercise_notice"

        if (
            re.search(r"\b(terminate|termination)\b", text, re.I)
            and re.search(
                r"\b(notice|notify|days? prior|written notice)\b",
                text, re.I
            )
        ):
            return "termination_notice"

        if re.search(r"\b(renew|renewal|renewed|extension)\b", text, re.I):
            return "renewal_period"

    if aspect == "payment":
        if (
            re.search(r"\b(within|no later than|due|payable)\b", text, re.I)
            and re.search(r"\b(invoice|payment|payable|pay)\b", text, re.I)
        ):
            return "payment_deadline"

    if aspect == "confidentiality":
        if re.search(
            r"\b(confidentiality|confidential information)\b", text, re.I
        ):
            return "confidentiality_period"

    return None


def _duration_context(text, duration):
    start = duration["start"]
    end = duration["end"]

    # Use a bounded local window around each duration.
    # This avoids treating every duration in a long clause as equivalent.
    left = max(0, start - 140)
    right = min(len(text), end + 100)

    context = text[left:right].lower()

    # Identify the local contractual purpose of the duration.
    if re.search(r"\b(initial|original)\s+(?:term|period)\b", context):
        return "initial_term"

    if re.search(r"\b(renewal|renewed|successive)\s+(?:term|period)\b", context):
        return "renewal_period"

    if re.search(r"\b(non[- ]renewal|nonrenewal)\b", context):
        return "non_renewal_notice"

    if re.search(r"\b(cure|remedy|remedial)\b", context):
        return "cure_period"

    if re.search(r"\b(transition[- ]out|transition period|wind[- ]down)\b", context):
        return "transition_period"

    if re.search(r"\b(renew|renewal|option to renew|choice to renew)\b", context):
        return "renewal_exercise_notice"

    if re.search(r"\b(terminate|termination)\b", context):
        return "termination_notice"

    if re.search(r"\b(invoice|payment|payable)\b", context):
        return "payment_deadline"

    return None


def _duration_records(text):
    records = []

    for duration in _dur(text):
        records.append({
            **duration,
            "context_role": _duration_context(text, duration),
        })

    return records


def _comparable_durations(text_a, text_b, role_a, role_b):
    records_a = _duration_records(text_a)
    records_b = _duration_records(text_b)

    comparable = []

    for left in records_a:
        for right in records_b:

            if left["unit"] != right["unit"]:
                continue

            if left["value"] == right["value"]:
                continue

            # If both durations have a detected local role,
            # require the local roles to match.
            if (
                left["context_role"]
                and right["context_role"]
                and left["context_role"] != right["context_role"]
            ):
                continue

            # Avoid comparing a clearly identified initial term
            # with a renewal period or a notice period.
            if (
                left["context_role"] in {
                    "initial_term", "renewal_period",
                    "renewal_exercise_notice", "non_renewal_notice",
                    "cure_period", "transition_period",
                    "termination_notice", "payment_deadline",
                }
                and right["context_role"] in {
                    "initial_term", "renewal_period",
                    "renewal_exercise_notice", "non_renewal_notice",
                    "cure_period", "transition_period",
                    "termination_notice", "payment_deadline",
                }
                and left["context_role"] != right["context_role"]
            ):
                continue

            if role_a == "renewal_period" and role_b == "renewal_period":
                if left["context_role"] == "initial_term":
                    continue
                if right["context_role"] == "initial_term":
                    continue

            comparable.append((left, right))

    return comparable


def _normalize_cap(value):
    value = value.casefold()
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"\s*([(),])\s*", r"\1", value)
    value = value.strip(" \t\r\n.,;")
    return value


def detect_cross_clause_risks(clauses):
    out = []

    for a, b in combinations(clauses, 2):
        shared = set(a.get("aspects", [])) & set(b.get("aspects", []))

        text_a = a.get("text", "") or ""
        text_b = b.get("text", "") or ""

        normalized_a = _normalize_clause(text_a)
        normalized_b = _normalize_clause(text_b)

        identical_clauses = normalized_a == normalized_b

        for aspect in ("payment", "termination", "confidentiality"):
            if aspect not in shared or identical_clauses:
                continue

            role_a = _duration_role(text_a, aspect)
            role_b = _duration_role(text_b, aspect)

            if not role_a or role_a != role_b:
                continue

            comparable = _comparable_durations(
                text_a, text_b, role_a, role_b
            )

            if comparable:
                left, right = comparable[0]

                out.append({
                    "risk_type": aspect + "_duration_difference",
                    "severity": "medium",
                    "clauses": [a["id"], b["id"]],
                    "claim": (
                        f"Different {aspect} periods appear in related clauses."
                    ),
                    "rationale": (
                        "Candidate only. The provisions have the same detected "
                        "duration role and locally matched duration context; "
                        "review parties, triggering events, scope, precedence "
                        "and exceptions before treating them as a conflict."
                    ),
                    "signals": {
                        "duration_role": role_a,
                        "duration_a": (
                            left["value"], left["unit"], left["text"]
                        ),
                        "duration_b": (
                            right["value"], right["unit"], right["text"]
                        ),
                        "local_role_a": left["context_role"],
                        "local_role_b": right["context_role"],
                    },
                })

        if "liability" in shared and not identical_clauses:
            cap_a = re.search(
                r"(?:limited to|shall not exceed|capped at)\s+([^.;\n]+)",
                text_a, re.I
            )
            cap_b = re.search(
                r"(?:limited to|shall not exceed|capped at)\s+([^.;\n]+)",
                text_b, re.I
            )

            if (
                cap_a and cap_b
                and _normalize_cap(cap_a.group(1))
                != _normalize_cap(cap_b.group(1))
            ):
                out.append({
                    "risk_type": "liability_cap_difference",
                    "severity": "high",
                    "clauses": [a["id"], b["id"]],
                    "claim": "Different liability cap expressions appear.",
                    "rationale": (
                        "Check whether the clauses govern different claim types "
                        "or contain carve-outs. This is a review candidate, "
                        "not a confirmed conflict."
                    ),
                })

        if "exception" in shared and shared & {"liability", "confidentiality"}:
            out.append({
                "risk_type": "exception_scope_review",
                "severity": "low",
                "clauses": [a["id"], b["id"]],
                "claim": (
                    "An exception-related clause shares a risk domain "
                    "with another clause."
                ),
                "rationale": (
                    "Review whether the exception modifies, overrides "
                    "or is unrelated to the other provision."
                ),
            })

    return out
