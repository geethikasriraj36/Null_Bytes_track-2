"""Classical baseline: identical features, RBF kernel. Q-Gate must be compared to this."""
import numpy as np
from sklearn.svm import SVC
from aegis.qgate.embed import make_embedder

class RBFBaseline:
    def fit(self, texts, labels):
        self.emb = make_embedder()
        self.svm = SVC(kernel="rbf", gamma="scale", class_weight="balanced")
        self.svm.fit(self.emb.fit_transform(texts), labels)
        return self
    def proba(self, texts):
        return 1 / (1 + np.exp(-2 * self.svm.decision_function(self.emb.transform(texts))))

    def score(self, text):
        from aegis.qgate.detector import REVIEW_AT, QUARANTINE_AT
        from aegis.contracts import Verdict
        p = float(self.proba([text])[0])
        d = "quarantine" if p >= QUARANTINE_AT else "review" if p >= REVIEW_AT else "pass"
        return Verdict(layer="RBF", decision=d, score=p)
    def save(self, path="models/rbf.pkl"):
        import pickle; from pathlib import Path
        Path(path).parent.mkdir(exist_ok=True); pickle.dump(self, open(path, "wb"))
    @staticmethod
    def load(path="models/rbf.pkl"):
        import pickle; return pickle.load(open(path, "rb"))
