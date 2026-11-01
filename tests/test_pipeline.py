from src.contractgraph.pipeline import analyze_contract
from src.contractgraph.sample_data import SAMPLE_CONTRACT
from src.contractgraph.evidence import verify_evidence
from src.contractgraph.evaluation import classification_metrics,retrieval_recall_at_k
def test_pipeline():
    r=analyze_contract(SAMPLE_CONTRACT)
    assert r["status"]=="success" and len(r["clauses"])>=5
def test_traceability():
    x=verify_evidence([{"clauses":["C1"],"claim":"x"}],{"C1":{"text":"source"}})[0]
    assert x["evidence_verified"] and not x["semantic_support_assessed"]
def test_bad_id():
    assert not verify_evidence([{"clauses":["C9"],"evidence":["x"]}],{})[0]["evidence_verified"]
def test_metrics():
    m=classification_metrics([1,1,0,0],[1,0,1,0])
    assert m["tp"]==1 and m["fp"]==1 and m["fn"]==1 and m["f1"]==.5
def test_recall():
    assert retrieval_recall_at_k(["C1","C2"],["C2","C3"],2)==.5
