"""E1 + E2, offline (no LLM calls). Run: python -m scripts.eval_qgate
E1: Q-Gate vs RBF baseline on held-out data (same features, same split).
E2: incremental catches = injections Q-Gate flags that BOTH the RBF baseline and the Line 1 heuristics miss."""
import json
from pathlib import Path
import numpy as np
from sklearn.metrics import roc_auc_score, precision_score, recall_score
from aegis.adapters import REVIEW_AT, load_qgate, load_rbf
from aegis.inputguard.classify import heuristic_score

rows = [json.loads(l) for l in Path("data/qgate_test.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
X, y = [r["text"] for r in rows], np.array([r["label"] for r in rows])
q, r = load_qgate().proba(X), load_rbf().proba(X)
h = np.array([heuristic_score([t]) for t in X])
out = {}
for name, s in [("qgate", q), ("rbf", r)]:
    pred = s >= REVIEW_AT
    out[name] = {"auroc": roc_auc_score(y, s), "recall": recall_score(y, pred),
                 "precision": precision_score(y, pred, zero_division=0), "fpr": float(pred[y == 0].mean())}
inc = (y == 1) & (q >= REVIEW_AT) & (r < REVIEW_AT) & (h < 0.4)
rbf_only = (y == 1) & (r >= REVIEW_AT) & (q < REVIEW_AT) & (h < 0.4)
out["E2"] = {"n_attacks": int(y.sum()), "qgate_only_catches": int(inc.sum()), "rbf_only_catches": int(rbf_only.sum()),
             "examples": [X[i][:120] for i in np.where(inc)[0][:5]]}
Path("results").mkdir(exist_ok=True)
Path("results/qgate_e1_e2.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
