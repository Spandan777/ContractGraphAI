import re
PATTERNS = {
 "payment": r"\b(payment|invoice|fee|payable|compensation)\b",
 "termination": r"\b(termination|terminate|notice period|expiry)\b",
 "liability": r"\b(liability|liable|damages|indemnif|limitation of)\b",
 "confidentiality": r"\b(confidential|non-disclosure|disclose|proprietary information)\b",
 "obligation": r"\b(shall|must|required to|undertakes)\b",
 "exception": r"\b(except|excluding|notwithstanding|provided that|unless)\b",
 "governing_law": r"\b(governing law|jurisdiction|venue)\b",
}
def enrich_clauses(clauses):
    out=[]
    for c in clauses:
        aspects=[k for k,p in PATTERNS.items() if re.search(p,c["text"],re.I)]
        durations=[{"value":int(n),"unit":u.lower()} for n,u in re.findall(
            r"\b(\d{1,4})\)?\s*(business days?|days?|weeks?|months?|years?)\b",c["text"],re.I)]
        out.append({**c,"aspects":aspects,"durations":durations})
    return out
def split_clauses(text):
    paragraphs=[p.strip() for p in re.split(r"\n\s*\n+",text) if p.strip()]
    clauses=[]
    for p in paragraphs:
        if len(p)<25 and clauses:
            clauses[-1]["text"] += "\n"+p
        else:
            i=len(clauses)+1
            clauses.append({"id":f"C{i}","title":p.splitlines()[0][:100],"text":p})
    if not clauses and text.strip(): clauses=[{"id":"C1","title":"Clause 1","text":text.strip()}]
    return enrich_clauses(clauses)
