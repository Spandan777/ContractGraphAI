import re
REFS=[r"\b(?:as set out|as described|subject) in (?:section|clause)\s+([\w.-]+)",
      r"\b(?:pursuant to|under|in accordance with) (?:section|clause)\s+([\w.-]+)"]
def build_dependency_graph(clauses):
    import networkx as nx
    g=nx.MultiDiGraph()
    for c in clauses: g.add_node(c["id"],title=c["title"],aspects=c["aspects"])
    for i,a in enumerate(clauses):
        for b in clauses[i+1:]:
            shared=sorted(set(a["aspects"])&set(b["aspects"]))
            if shared:
                g.add_edge(a["id"],b["id"],relation="shared_aspect",
                    reason="Shared tags: "+", ".join(shared),method="keyword_heuristic",confidence=.55)
            if set(shared)&{"payment","termination","liability","confidentiality"}:
                g.add_edge(a["id"],b["id"],relation="potential_conflict",
                    reason="Same risk domain; compare scope, triggers and exceptions.",
                    method="candidate_generation",confidence=.35)
        for pat in REFS:
            for target in re.findall(pat,a["text"],re.I):
                for b in clauses:
                    if b["id"].lower()==target.lower() or b["title"].lower().startswith(target.lower()):
                        g.add_edge(a["id"],b["id"],relation="explicit_reference",
                            reason=f"Explicit reference to {target}",method="regex",confidence=.85)
    return g
def edges_as_dicts(g):
    return [{"source":u,"target":v,**d} for u,v,d in g.edges(data=True)]
