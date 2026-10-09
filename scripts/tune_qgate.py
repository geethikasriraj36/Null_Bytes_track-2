"""Tune Q-Gate and the RBF baseline with the SAME effort, on the TRAIN split only (5-fold CV).
Run: python -m scripts.tune_qgate        -> prints CV AUROC per setting, writes results/qgate_tuning.json
Both models get the same C grid on the same folds and the same 4 features; the test split is never touched."""
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.svm import SVC

from aegis.qgate.embed import TextEmbedder
from aegis.qgate.kernel import gram

C_GRID = [0.1, 0.3, 1.0, 3.0, 10.0, 30.0]

rows = [json.loads(l) for l in Path("data/qgate_train.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
X = [r["text"] for r in rows]
y = np.array([int(r["label"]) for r in rows])
folds = list(StratifiedKFold(n_splits=5, shuffle=True, random_state=0).split(X, y))

scores = {"qgate": {c: [] for c in C_GRID}, "rbf": {c: [] for c in C_GRID}}
for k, (tr, va) in enumerate(folds, 1):
    emb = TextEmbedder().fit([X[i] for i in tr])                  # features fitted on the fold's train part only
    Ftr, Fva = emb.transform([X[i] for i in tr]), emb.transform([X[i] for i in va])
    Ktr, Kva = gram(Ftr), gram(Fva, Ftr)
    for c in C_GRID:
        q = SVC(kernel="precomputed", C=c, class_weight="balanced").fit(Ktr, y[tr])
        scores["qgate"][c].append(roc_auc_score(y[va], q.decision_function(Kva)))
        r = SVC(kernel="rbf", gamma="scale", C=c, class_weight="balanced").fit(Ftr, y[tr])
        scores["rbf"][c].append(roc_auc_score(y[va], r.decision_function(Fva)))
    print(f"fold {k}/5 done")

out = {}
for model, by_c in scores.items():
    table = {str(c): round(float(np.mean(v)), 4) for c, v in by_c.items()}
    best = max(by_c, key=lambda c: np.mean(by_c[c]))
    out[model] = {"cv_auroc_by_C": table, "best_C": best, "best_cv_auroc": round(float(np.mean(by_c[best])), 4)}
    print(model, table, "-> best C =", best)

Path("results").mkdir(exist_ok=True)
Path("results/qgate_tuning.json").write_text(json.dumps(out, indent=2))
