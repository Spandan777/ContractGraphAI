from datetime import datetime,timezone
from .ingestion import extract_text,validate_document
from .clauses import split_clauses
from .retrieval import retrieve
from .graph import build_dependency_graph,edges_as_dicts
from .risks import detect_cross_clause_risks
from .evidence import verify_evidence
from .gemini import analyze_with_gemini
QUERIES={"payment":"payment invoice fees deadline","termination":"termination expiry notice period",
 "liability":"liability indemnification damages limitation cap",
 "confidentiality":"confidential information disclosure duration"}
def analyze_contract(source,use_gemini=False):
    text=extract_text(source); validation=validate_document(text)
    if not validation["valid"]:
        return {"status":"invalid","validation":validation,"clauses":[],"graph_edges":[],
                "baseline_retrieval":{},"verified_findings":[]}
    clauses=split_clauses(text); by={c["id"]:c for c in clauses}
    graph=build_dependency_graph(clauses); rules=detect_cross_clause_risks(clauses)
    gem=analyze_with_gemini(clauses) if use_gemini else {"status":"disabled","findings":[]}
    return {"status":"success","validation":validation,"clauses":clauses,
      "graph_nodes":list(graph.nodes(data=True)),"graph_edges":edges_as_dicts(graph),
      "baseline_retrieval":{k:retrieve(q,clauses,3) for k,q in QUERIES.items()},
      "rule_findings":rules,"verified_findings":verify_evidence(rules,by),
      "gemini":{**gem,"verified_findings":verify_evidence(gem.get("findings",[]),by)},
      "generated_at":datetime.now(timezone.utc).isoformat()}
