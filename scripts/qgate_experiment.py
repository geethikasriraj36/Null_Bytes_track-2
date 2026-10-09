"""Q-Gate design experiment (no API): qubits 4 / 6 / 8 x character vs word features.
Run: python -m scripts.qgate_experiment      -> results/qgate_experiment.json

Uses the exact closed form of the ZZ feature-map state (verified against PennyLane in tests/test_adapters.py):
every amplitude is 2^-n/2 and the phase of basis state b is
  sum_i s(b_i) x_i / 2 + sum_i s(b_i XOR b_i+1) (pi - x_i)(pi - x_i+1) / 2,   s(0) = -1, s(1) = +1.
Reports, per setting: 5-fold CV AUROC on TRAIN only, held-out TEST AUROC (deepset test split), and document-level
behaviour on our knowledge base (false flags) and on the demo doc (should be flagged)."""
import itertools
import json
import re
from pathlib import Path

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import MinMaxScaler
from sklearn.svm import SVC

PI = np.pi


def states(X):
    n = X.shape[1]
    bits = np.array(list(itertools.product([0, 1], repeat=n)))          # (2^n, n), qubit 0 = leftmost bit
    s = 2 * bits - 1
    par = 2 * (bits[:, :-1] ^ bits[:, 1:]) - 1                             # (2^n, n-1)
    th = (X @ s.T) / 2 + (((PI - X[:, :-1]) * (PI - X[:, 1:])) @ par.T) / 2   # (samples, 2^n)
    return np.exp(1j * th) / np.sqrt(2 ** n)


def gram(A, B):
    return np.abs(states(A).conj() @ states(B).T) ** 2


class Emb:
    """char: character 2-5 grams; word: word 1-2 grams; hybrid: half the qubits each."""
    def __init__(self, n, analyzer):
        def mk(a, k):
            v = (TfidfVectorizer(analyzer="char", ngram_range=(2, 5)) if a == "char"
                 else TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True))
            return v, TruncatedSVD(n_components=k, random_state=42)
        self.parts = [mk("char", n // 2), mk("word", n - n // 2)] if analyzer == "hybrid" else [mk(analyzer, n)]
        self.sc = MinMaxScaler((0, PI))

    def _raw(self, t, fit=False):
        return np.hstack([svd.fit_transform(v.fit_transform(t)) if fit else svd.transform(v.transform(t))
                          for v, svd in self.parts])

    def fit(self, t):
        self.sc.fit(self._raw(t, fit=True))
        return self

    def tr(self, t):
        return np.clip(self.sc.transform(self._raw(t)), 0, PI)


def sentences(text):
    s = [x for x in re.split(r"(?<=[.!?:])\s+|\n+", text) if len(x.strip()) > 15][:8]
    return s or [text]


def run(n, analyzer, C, Xtr, ytr, Xte, yte, docs, demo):
    sig = lambda m: 1 / (1 + np.exp(-m))
    cv = []
    for tr, va in StratifiedKFold(5, shuffle=True, random_state=0).split(Xtr, ytr):
        e = Emb(n, analyzer).fit([Xtr[i] for i in tr])
        Ftr, Fva = e.tr([Xtr[i] for i in tr]), e.tr([Xtr[i] for i in va])
        m = SVC(kernel="precomputed", C=C, class_weight="balanced").fit(gram(Ftr, Ftr), ytr[tr])
        cv.append(roc_auc_score(ytr[va], m.decision_function(gram(Fva, Ftr))))
    e = Emb(n, analyzer).fit(Xtr)
    F = e.tr(Xtr)
    m = SVC(kernel="precomputed", C=C, class_weight="balanced").fit(gram(F, F), ytr)
    score = lambda texts: sig(m.decision_function(gram(e.tr(texts), F)))
    test_auc = roc_auc_score(yte, score(Xte))
    doc_scores = {name: float(score(sentences(t)).max()) for name, t in docs.items()}
    return {"qubits": n, "features": analyzer, "C": C, "cv_auroc": round(float(np.mean(cv)), 4),
            "test_auroc": round(float(test_auc), 4),
            "kb_docs_flagged": sum(v >= 0.5 for v in doc_scores.values()), "kb_docs": len(doc_scores),
            "worst_kb_doc": max(doc_scores.items(), key=lambda kv: kv[1]),
            "demo_doc_score": round(float(score(sentences(demo)).max()), 4)}


if __name__ == "__main__":
    load = lambda p: [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]
    tr, te = load("data/qgate_train.jsonl"), load("data/qgate_test.jsonl")
    Xtr, ytr = [r["text"] for r in tr], np.array([r["label"] for r in tr])
    Xte, yte = [r["text"] for r in te], np.array([r["label"] for r in te])
    docs = {f.name: f.read_text(encoding="utf-8") for f in Path("data/docs").glob("*.md") if not f.name.startswith("demo_")}
    demo = Path("data/docs/demo_vendor_update.md").read_text(encoding="utf-8")
    out = []
    for n, a in itertools.product([4, 6, 8], ["char", "word", "hybrid"]):
        best = max((run(n, a, C, Xtr, ytr, Xte, yte, docs, demo) for C in [1.0, 10.0, 30.0]), key=lambda r: r["cv_auroc"])
        out.append(best)
        print(f"{n} qubits {a:4s} C={best['C']:<4} cv {best['cv_auroc']:.3f}  test {best['test_auroc']:.3f}  "
              f"KB false flags {best['kb_docs_flagged']}/{best['kb_docs']}  demo {best['demo_doc_score']:.2f}")
    Path("results").mkdir(exist_ok=True)
    Path("results/qgate_experiment.json").write_text(json.dumps(out, indent=2))
