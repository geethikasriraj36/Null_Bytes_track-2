"""Train Q-Gate and the RBF baseline on the SAME split. Run: python -m scripts.train_qgate
Input:  data/qgate_train.jsonl  lines of {"text": ..., "label": 0|1}   (1 = injection)
Output: models/qgate.pkl, models/rbf.pkl"""
import json, random, time
from pathlib import Path
from aegis.qgate.detector import QGate
from aegis.qgate.baseline_rbf import RBFBaseline

rows = [json.loads(l) for l in Path("data/qgate_train.jsonl").read_text().splitlines() if l.strip()]
random.Random(0).shuffle(rows)
rows = rows[:600]                                    # statevector kernel: 600 rows train in well under a minute
X, y = [r["text"] for r in rows], [int(r["label"]) for r in rows]
print(f"training on {len(X)} rows, {sum(y)} injections")
t = time.time(); QGate().fit(X, y).save(); print(f"Q-Gate trained in {time.time() - t:.0f}s")
RBFBaseline().fit(X, y).save(); print("RBF baseline trained")
