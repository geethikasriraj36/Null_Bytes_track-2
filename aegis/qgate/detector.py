"""Q-Gate: quantum-kernel SVM. Advisory only: pass / review / quarantine."""
import pickle, re, time
from pathlib import Path
import numpy as np
from sklearn.svm import SVC
from aegis.contracts import Verdict
from aegis.qgate import kernel
from aegis.qgate.embed import make_embedder

MODEL = Path("models/qgate.pkl")
REVIEW_AT, QUARANTINE_AT = 0.5, 0.8          # tune on the dev split, then freeze

class QGate:
    def fit(self, texts, labels):
        self.emb = make_embedder()
        self.Xtr = self.emb.fit_transform(texts)
        K = kernel.gram(self.Xtr)
        self.svm = SVC(kernel="precomputed", class_weight="balanced")
        self.svm.fit(K, labels)
        return self

    def proba(self, texts) -> np.ndarray:
        """Injection probability-like score in 0..1 (sigmoid of the SVM margin).
        Only support vectors affect the margin, so we compute the kernel against them only."""
        X = self.emb.transform(texts)
        K = np.zeros((len(X), len(self.Xtr)))
        sv = self.svm.support_                 # only support vectors change the margin
        K[:, sv] = kernel.gram(X, self.Xtr[sv])
        return 1 / (1 + np.exp(-2 * self.svm.decision_function(K)))

    def score(self, text: str) -> Verdict:
        """Scores each sentence and keeps the max: an injected sentence hidden in a
        benign paragraph would otherwise be averaged away."""
        t = time.perf_counter()
        sents = [s for s in re.split(r"(?<=[.!?:])\s+|\n+", text) if len(s.strip()) > 15][:8] or [text]
        p = float(self.proba(sents).max())
        d = "quarantine" if p >= QUARANTINE_AT else "review" if p >= REVIEW_AT else "pass"
        return Verdict(layer="QGATE", decision=d, score=p,
                       details={"ms": round((time.perf_counter() - t) * 1000)})

    def save(self, path=MODEL):
        path.parent.mkdir(exist_ok=True); pickle.dump(self, path.open("wb"))

    @staticmethod
    def load(path=MODEL) -> "QGate":
        return pickle.load(path.open("rb"))
