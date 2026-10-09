"""Train Q-Gate and the RBF baseline on the SAME split and the SAME 4 features. Run: python -m scripts.train_qgate
Input:  data/qgate_train.jsonl  lines of {"text": ..., "label": 0|1}   (1 = injection)
Output: models/qgate.pkl (M3's QGate), models/rbf.pkl (M3's RBFBaseline + the Q-Gate embedder)"""
import json, random, time
from pathlib import Path

import joblib

from aegis.adapters import QGATE_MODEL, RBF_MODEL
from aegis.qgate.baseline_rbf import RBFBaseline
from aegis.qgate.detector import QGate

rows = [json.loads(l) for l in Path("data/qgate_train.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
random.Random(0).shuffle(rows)
rows = rows[:600]                                    # statevector kernel: 600 rows train in well under a minute
X, y = [r["text"] for r in rows], [int(r["label"]) for r in rows]
print(f"training on {len(X)} rows, {sum(y)} injections")

# C picked by scripts/tune_qgate.py (5-fold CV on train only, same grid for both); defaults if not tuned yet
tuned = Path("results/qgate_tuning.json")
best = json.loads(tuned.read_text()) if tuned.exists() else {}
c_q, c_r = best.get("qgate", {}).get("best_C", 1.0), best.get("rbf", {}).get("best_C", 1.0)
print(f"C: qgate={c_q}  rbf={c_r}" + ("" if tuned.exists() else "  (untuned: run python -m scripts.tune_qgate)"))

t = time.time()
qgate = QGate(C=c_q).fit(X, y)
qgate.train_texts, qgate.train_labels = list(X), list(y)    # lets the UI show the closest known examples
qgate.save(QGATE_MODEL)
print(f"Q-Gate trained in {time.time() - t:.0f}s -> {QGATE_MODEL}")

# fairness: the classical twin sees exactly the features Q-Gate's kernel sees
features = qgate.embedder.transform(X)
rbf = RBFBaseline(C=c_r).fit(features, y)
RBF_MODEL.parent.mkdir(parents=True, exist_ok=True)
joblib.dump({"embedder": qgate.embedder, "rbf": rbf}, RBF_MODEL)
print(f"RBF baseline trained -> {RBF_MODEL}")
