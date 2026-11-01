ABLATIONS=[
("A1","Independent retrieval"),("A2","Retrieval + aspect tagging"),
("A3","Retrieval + graph candidates"),("A4","Graph + cross-clause rules"),
("A5","Full pipeline + evidence traceability")]
def empty_results():
    return [{"id":i,"system":n,"precision":None,"recall":None,"f1":None,
             "evidence_accuracy":None,"n_evaluated":0,"status":"pending_gold_annotations"}
            for i,n in ABLATIONS]
