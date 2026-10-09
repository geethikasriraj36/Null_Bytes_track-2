"""Integration adapters (M1): M3's ingress + Q-Gate modules -> the frozen contract (guide section 10).

M3's code is used as written; this file only translates shapes:
  process(raw, source, origin, state, enabled) -> (contracts.ContentItem, [Verdict])
  scan(text) -> (redacted_text, finding_types)          canary_hit(text) -> bool
  load_qgate().score(text) -> Verdict(layer="QGATE")     load_rbf().score(text) -> Verdict(layer="RBF")
"""
import re
from pathlib import Path

import joblib
import numpy as np

from aegis.contracts import ContentItem, SessionState, Verdict
from aegis.grounding.prompt import CANARY
from aegis.ingress import process as m3_process
from aegis.ingress import scan as m3_scan

# ---------------------------------------------------------------- D2 / D3
# M3's synthetic canaries + the system-prompt canary (J2) + the planted secret-store canary (setup_data)
CANARIES = sorted(set(m3_scan.CANARIES) | {CANARY, "sk-canary-0000DEADBEEF"})

TYPE_NAMES = {"aws_access_key": "AWS_KEY", "payment_card": "CARD", "generic_secret": "API_KEY",
              "high_entropy_token": "HIGH_ENTROPY", "phone": "PHONE", "ipv4": "IPV4", "email": "EMAIL"}
# Emails are not redacted by default (as in the starter): the agent must see addresses so the
# deterministic layers (A2 taint, D4 allowlist) can block exfiltration, and legit replies like
# "Email queued to bob@ourcompany.com" are not counted as leaks.
SKIP_TYPES = {"email"}


def canary_hit(text: str) -> bool:
    return any(c in text for c in CANARIES)


def scan(text: str, redact_emails: bool = False) -> tuple[str, list[str]]:
    """M3's detectors (regex + Luhn + entropy); returns (redacted_text, finding_types)."""
    skip = set() if redact_emails else SKIP_TYPES
    hits = [m for m in m3_scan.scan(text)["matches"] if m["type"] not in skip]
    spans = sorted((m["start"], m["end"], TYPE_NAMES.get(m["type"], m["type"].upper())) for m in hits)
    merged: list[list] = []                                   # overlapping matches -> one redaction
    for start, end, kind in spans:
        if merged and start < merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end, kind])
    for start, end, kind in reversed(merged):
        text = text[:start] + f"[REDACTED:{kind}]" + text[end:]
    return text, [kind for _, _, kind in merged]


# ---------------------------------------------------------------- D1 + tagging
def label_for(origin: str) -> str:
    """Contract labels from provenance: files under secret/ are secret, FAQ/public docs are public."""
    if "secret" in origin:
        return "secret"
    if origin.startswith("public") or origin.endswith("faq.md"):
        return "public"
    return "internal"

M3_LABEL = {"public": "public", "internal": "internal", "secret": "confidential"}


def _role(permissions) -> str:
    """Contract permissions (labels a session may read) -> M3 role for its ACL table."""
    if "secret" in permissions:
        return "admin"
    return "agent" if "internal" in permissions else "user"


def process(raw: str, source: str, origin: str, state: SessionState, enabled: bool = True) -> tuple[ContentItem, list[Verdict]]:
    """Ingress: D1 ACL (M3) -> D3 canary check -> D2 redaction (M3 detectors) -> provenance + taint."""
    label = label_for(origin)
    item = ContentItem(text=raw, source=source, origin=origin, label=label, tainted=source != "user")
    if not enabled:
        return item, []
    v = []
    m3 = m3_process.process(raw or " ", source=origin or source, label=M3_LABEL[label],
                            user_role=_role(state.permissions), redact_sensitive=False)
    if not m3.accessible:                                                   # D1
        item.text = "[ACCESS DENIED]"
        v.append(Verdict(layer="D1", decision="block", score=1, reason="acl"))
    if canary_hit(item.text):                                               # D3, before redaction hides it
        v.append(Verdict(layer="D3", decision="flag", score=1, reason="canary_in_ingress"))
    item.text, found = scan(item.text)                                      # D2
    item.redactions = len(found)
    if found:
        v.append(Verdict(layer="D2", decision="redact", score=0.5, details={"types": found}))
    if item.tainted:
        state.seen_tainted = True
    if item.label in ("internal", "secret"):
        state.seen_private = True
    return item, v


# ---------------------------------------------------------------- Q-Gate / RBF
QGATE_MODEL, RBF_MODEL = Path("models/qgate.pkl"), Path("models/rbf.pkl")
REVIEW_AT, QUARANTINE_AT = 0.5, 0.8          # tune on a dev split carved from train, then freeze


def sentences(text: str) -> list[str]:
    """Score each sentence and keep the max: an injected sentence hidden in a benign paragraph
    would otherwise be averaged away. Max 8 sentences per chunk."""
    sents = [s for s in re.split(r"(?<=[.!?:])\s+|\n+", text) if len(s.strip()) > 15][:8]
    return sents or [text if text.strip() else "(empty)"]


def _verdict(layer: str, p: float, ms: float) -> Verdict:
    d = "quarantine" if p >= QUARANTINE_AT else "review" if p >= REVIEW_AT else "pass"
    return Verdict(layer=layer, decision=d, score=round(p, 4), details={"ms": round(ms)})


class QGateDetector:
    """M3's QGate (quantum-kernel SVM) behind the contract: score(text) -> Verdict(layer="QGATE")."""
    layer = "QGATE"

    def __init__(self, model):
        self.model = model
        self._train_states = None

    def _kernel(self, texts):
        """Fidelity kernel |<phi(x)|phi(train)>|^2 of each text against every training example,
        with the training states simulated once and cached (~1.7 s -> ~ms per call)."""
        from aegis.qgate.kernel import quantum_state
        if self._train_states is None:
            self._train_states = np.array([quantum_state(x) for x in self.model.X_train])
        feats = self.model.embedder.transform(list(texts))
        states = np.array([quantum_state(f) for f in feats])
        return np.clip(np.abs(states.conj() @ self._train_states.T) ** 2, 0.0, 1.0), feats

    def proba(self, texts) -> np.ndarray:
        """Same math as M3's QGate.score: sigmoid of the SVM margin on the fidelity kernel."""
        K, _ = self._kernel(texts)
        margins = np.asarray(self.model.model.decision_function(K), dtype=float).reshape(-1)
        return 1 / (1 + np.exp(-margins))

    def _explain(self, sentence: str) -> dict:
        """Evidence for the top sentence: its 4 features (the qubit angles) and the training examples
        whose quantum states overlap most with it. Needs a model trained by scripts/train_qgate."""
        K, feats = self._kernel([sentence])
        out = {"features": [round(float(f), 3) for f in feats[0]]}
        texts, labels = getattr(self.model, "train_texts", None), getattr(self.model, "train_labels", None)
        if texts is not None and labels is not None:
            order = np.argsort(-K[0])
            near = lambda lab, n: [{"text": texts[i][:160], "k": round(float(K[0, i]), 3)}
                                   for i in order if labels[i] == lab][:n]
            out["nearest_attacks"], out["nearest_benign"] = near(1, 3), near(0, 1)
        return out

    def score(self, text: str) -> Verdict:
        import time
        t = time.perf_counter()
        sents = sentences(text)
        ps = self.proba(sents)
        top = int(ps.argmax())
        v = _verdict(self.layer, float(ps[top]), 0)
        v.details.update({"sentences": [{"text": s[:200], "score": round(float(p), 4)} for s, p in zip(sents, ps)],
                          "top": top, **self._explain(sents[top])})
        v.details["ms"] = round((time.perf_counter() - t) * 1000)
        return v


class RBFDetector(QGateDetector):
    """M3's RBFBaseline on the SAME 4 features as Q-Gate (the embedder Q-Gate was trained with)."""
    layer = "RBF"

    def __init__(self, embedder, rbf):
        self.embedder, self.rbf = embedder, rbf

    def _explain(self, sentence: str) -> dict:
        return {}

    def proba(self, texts) -> np.ndarray:
        margins = np.asarray(self.rbf.score(self.embedder.transform(list(texts))), dtype=float)
        return 1 / (1 + np.exp(-margins))                  # same sigmoid-of-margin as QGate.score


def load_qgate(path=QGATE_MODEL) -> QGateDetector:
    from aegis.qgate.detector import QGate
    return QGateDetector(QGate.load(path))


def load_rbf(path=RBF_MODEL) -> RBFDetector:
    bundle = joblib.load(path)
    return RBFDetector(bundle["embedder"], bundle["rbf"])
