"""Clause segmentation and deterministic attribute enrichment."""
from __future__ import annotations

import re
from .attribute_extraction import extract_clause_attributes

HEADING = re.compile(
    r"(?im)^\s*((?:\d+(?:\.\d+)*[.)]?\s+)|(?:section\s+\d+(?:\.\d+)*\s*[:.-]?\s*)|"
    r"(?:article\s+[ivx\d]+\s*[:.-]?\s*)|(?:[A-Z][A-Z0-9 ,/&()-]{3,80}))"
)

def enrich_clauses(clauses):
    out = []
    for clause in clauses:
        attrs = extract_clause_attributes(clause.get("text", ""))
        out.append({**clause, **attrs})
    return out

def split_clauses(text):
    if not isinstance(text, str) or not text.strip():
        return []
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    chunks, current = [], []
    for line in lines:
        is_heading = bool(re.match(
            r"^\s*(?:(?:\d+(?:\.\d+)*[.)]?)|(?:section\s+\d)|"
            r"(?:article\s+[ivx\d]+))\s+", line, re.I
        ))
        if is_heading and current and any(x.strip() for x in current):
            chunks.append("\n".join(current).strip())
            current = [line]
        else:
            current.append(line)
    if current and any(x.strip() for x in current):
        chunks.append("\n".join(current).strip())
    if len(chunks) <= 1:
        chunks = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
    merged = []
    for chunk in chunks:
        if len(chunk) < 25 and merged:
            merged[-1] += "\n" + chunk
        else:
            merged.append(chunk)
    clauses = []
    for i, chunk in enumerate(merged, 1):
        first = next((x.strip() for x in chunk.splitlines() if x.strip()), f"Clause {i}")
        clauses.append({
            "id": f"C{i}", "title": first[:120], "text": chunk, "index": i
        })
    return enrich_clauses(clauses)
