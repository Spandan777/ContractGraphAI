def classification_metrics(y_true,y_pred):
    tp=sum(bool(a) and bool(b) for a,b in zip(y_true,y_pred))
    fp=sum(not bool(a) and bool(b) for a,b in zip(y_true,y_pred))
    fn=sum(bool(a) and not bool(b) for a,b in zip(y_true,y_pred))
    p=tp/(tp+fp) if tp+fp else 0.0; r=tp/(tp+fn) if tp+fn else 0.0
    return {"tp":tp,"fp":fp,"fn":fn,"precision":p,"recall":r,
            "f1":2*p*r/(p+r) if p+r else 0.0}
def retrieval_recall_at_k(ids,relevant,k):
    relevant=set(relevant)
    return len(set(ids[:k])&relevant)/len(relevant) if relevant else 0.0
def evidence_accuracy(rows):
    rows=list(rows)
    return sum(bool(x.get("evidence_verified"))==bool(x.get("gold_traceable")) for x in rows)/len(rows) if rows else 0.0
