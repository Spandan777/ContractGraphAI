import re
from itertools import combinations
DURATION=re.compile(r"\b(\d{1,4})\)?\s*(business days?|days?|weeks?|months?|years?)\b",re.I)
def _dur(text): return [(int(n),u.lower().rstrip("s")) for n,u in DURATION.findall(text)]
def detect_cross_clause_risks(clauses):
    out=[]
    for a,b in combinations(clauses,2):
        shared=set(a["aspects"])&set(b["aspects"])
        for aspect in ("payment","termination","confidentiality"):
            da,db=_dur(a["text"]),_dur(b["text"])
            anchor = {
                "payment": r"\b(invoice|payment|payable)\b",
                "termination": r"\b(notice|may terminate|written notice)\b",
                "confidentiality": r"\b(confidentiality|confidential information)\b",
            }[aspect]
            if (aspect in shared and da and db and da[0]!=db[0]
                and re.search(anchor, a["text"], re.I)
                and re.search(anchor, b["text"], re.I)):
                out.append({"risk_type":aspect+"_duration_difference","severity":"medium",
                    "clauses":[a["id"],b["id"]],
                    "claim":f"Different {aspect} periods appear in related clauses.",
                    "rationale":"Candidate only. Review scope, trigger, precedence and exceptions before treating as conflict."})
        if "liability" in shared:
            ca=re.search(r"(?:limited to|shall not exceed|capped at)\s+([^.;\n]+)",a["text"],re.I)
            cb=re.search(r"(?:limited to|shall not exceed|capped at)\s+([^.;\n]+)",b["text"],re.I)
            if ca and cb and ca.group(1).strip().lower()!=cb.group(1).strip().lower():
                out.append({"risk_type":"liability_cap_difference","severity":"high",
                    "clauses":[a["id"],b["id"]],"claim":"Different liability cap expressions appear.",
                    "rationale":"Check whether the clauses govern different claim types or contain carve-outs."})
        if "exception" in shared and shared&{"liability","confidentiality"}:
            out.append({"risk_type":"exception_scope_review","severity":"low","clauses":[a["id"],b["id"]],
                "claim":"An exception-related clause shares a risk domain with another clause.",
                "rationale":"Review whether the exception modifies, overrides or is unrelated to the other provision."})
    return out
