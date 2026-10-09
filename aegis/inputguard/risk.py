"""J3: decaying per-session risk score."""
from aegis.contracts import SessionState, Verdict
DECAY, STRICT_AT, END_AT = 0.7, 0.8, 1.6

def update(state: SessionState, j1: Verdict) -> Verdict:
    state.risk = state.risk * DECAY + (j1.score if j1.decision != "pass" else 0.0)
    if state.risk >= END_AT:
        return Verdict(layer="J3", decision="refuse", score=state.risk, reason="session_risk")
    if state.risk >= STRICT_AT:
        state.strict = True
        return Verdict(layer="J3", decision="strict", score=state.risk)
    return Verdict(layer="J3", decision="pass", score=state.risk)
