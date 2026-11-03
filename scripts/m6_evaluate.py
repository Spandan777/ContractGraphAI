import argparse, json
from pathlib import Path
from collections import Counter
from contractgraph.m6_annotations import read_jsonl, LABELS
p = argparse.ArgumentParser(description="Evaluate predictions against adjudicated M6 gold labels")
p.add_argument("gold_annotations")
p.add_argument("predictions")
p.add_argument("--output", default="data/processed/m6_evaluation.json")
a = p.parse_args()
gold, errors = read_jsonl(a.gold_annotations), []
for i, r in enumerate(gold, 1):
    if r.get("review_status") != "adjudicated": errors.append(f"gold record {i} is not adjudicated")
    if r.get("label") not in LABELS: errors.append(f"gold record {i} has invalid label")
if errors:
    raise SystemExit("Invalid gold data:\n" + "\n".join(errors))
pred = read_jsonl(a.predictions)
def unique_index(rows, key, name):
    d = {}
    for r in rows:
        k = r.get(key)
        if not k or k in d: raise SystemExit(f"Missing or duplicate {key} in {name}: {k}")
        d[k] = r
    return d
g, pr = unique_index(gold, "candidate_id", "gold"), unique_index(pred, "candidate_id", "predictions")
missing = sorted(set(g)-set(pr)); extra = sorted(set(pr)-set(g))
if missing or extra: raise SystemExit(f"Prediction coverage mismatch. Missing={missing}; extra={extra}")
known = [(g[k]["label"], pr[k].get("predicted_label")) for k in sorted(g) if g[k]["label"] != "uncertain"]
if any(y not in {"risk", "no_risk"} for _,y in known): raise SystemExit("Predicted labels must be risk or no_risk")
if not known: raise SystemExit("No binary gold records available; all labels are uncertain")
labels = ["risk", "no_risk"]
cm = {x:{y:sum(t==x and p==y for t,p in known) for y in labels} for x in labels}
tp=cm['risk']['risk']; fp=cm['no_risk']['risk']; fn=cm['risk']['no_risk']; tn=cm['no_risk']['no_risk']
precision=tp/(tp+fp) if tp+fp else 0.0; recall=tp/(tp+fn) if tp+fn else 0.0
f1=2*precision*recall/(precision+recall) if precision+recall else 0.0
accuracy=(tp+tn)/len(known)
report={"n_gold_total":len(g),"n_binary_evaluated":len(known),"n_uncertain_excluded":sum(r['label']=='uncertain' for r in g.values()),
        "confusion_matrix":cm,"tp":tp,"fp":fp,"fn":fn,"tn":tn,
        "precision_risk":precision,"recall_risk":recall,"f1_risk":f1,"accuracy":accuracy,
        "note":"Metrics are valid only for adjudicated labels and predictions on the held-out test split. This script does not enforce which split was used."}
Path(a.output).parent.mkdir(parents=True, exist_ok=True)
Path(a.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2)); print(f"Saved: {a.output}")
