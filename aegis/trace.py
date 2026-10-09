"""Per-turn trace for the UI's "stats for nerds" panel (M1).
The pipeline calls add() at each stage; run_turn/resume attach the result to TurnResult.trace.
Context-local, so parallel eval threads never mix traces. Never stores API keys; user text is truncated."""
import contextvars
import time

_T: contextvars.ContextVar[dict | None] = contextvars.ContextVar("aegis_trace", default=None)


def start(kind: str, **meta) -> None:
    _T.set({"kind": kind, "t0": time.perf_counter(), "steps": [], "llm": [], "audit_records": 0, **meta})


def add(stage: str, **data) -> None:
    t = _T.get()
    if t is not None:
        t["steps"].append({"stage": stage, "ms": round((time.perf_counter() - t["t0"]) * 1000), **data})


def llm_call(role: str, model: str, ms: float, tokens: int | None, ok: bool, error: str = "") -> None:
    t = _T.get()
    if t is not None:
        t["llm"].append({"role": role, "model": model, "ms": round(ms), "tokens": tokens, "ok": ok, "error": error})


def bump(key: str, n: int = 1) -> None:
    t = _T.get()
    if t is not None:
        t[key] = t.get(key, 0) + n


def finish() -> dict:
    t = _T.get()
    if t is None:
        return {}
    out = {k: v for k, v in t.items() if k != "t0"}
    out["total_ms"] = round((time.perf_counter() - t["t0"]) * 1000)
    out["llm_calls"] = len(t["llm"])
    out["llm_tokens"] = sum(c["tokens"] or 0 for c in t["llm"])
    return out
