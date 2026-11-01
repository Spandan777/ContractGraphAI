def verify_evidence(findings, by_id):
    """Checks source traceability only, not semantic entailment."""
    out=[]
    for f in findings:
        ids=f.get("clauses",[])
        ids_ok=(isinstance(ids,list) and bool(ids) and len(ids)==len(set(ids))
                and all(isinstance(x,str) and x in by_id for x in ids))
        ev=f.get("evidence",[])
        if not ev and ids_ok: ev=[by_id[x]["text"] for x in ids]
        ev_ok=(ids_ok and isinstance(ev,list) and len(ev)==len(ids)
               and all(isinstance(t,str) and t==by_id[c]["text"] for c,t in zip(ids,ev)))
        out.append({**f,"evidence":ev if isinstance(ev,list) else [],
            "evidence_verified":bool(ev_ok),"verification_scope":"source_traceability_only",
            "semantic_support_assessed":False,
            "verification_reason":"Exact source text matched." if ev_ok else "Clause IDs or evidence failed source matching."})
    return out
