"""Orchestrator. The ONLY place verdicts are combined and the agent loop runs.
run_turn(): a new user message.  resume(): after the human approves/denies a CONFIRM."""
import json, re
from aegis.config import CFG
from aegis.contracts import SessionState, ToolCall, TurnResult, Verdict, GateDecision
from aegis import llm
from aegis.audit import chain
from aegis.inputguard.normalize import normalize
from aegis.inputguard import classify, risk
from aegis.adapters import process, scan, canary_hit      # M3 ingress behind the section-10 contract
from aegis.line1 import taint, action_token
from aegis.toolsafety.gate import check_call, decide, REGISTRY
from aegis.tools.sim import execute, TOOLS, TOOL_SPECS
from aegis.grounding.prompt import SYSTEM, BASELINE_SYSTEM, wrap
from aegis.output.refusal import REFUSAL, ABSTAIN
from aegis.output import citation_check, nli
from aegis.output.decide import decide as h5_decide

MAX_STEPS = 5
GROUP = {"A1": "LINE1", "A2": "LINE1", "A3": "LINE1", "D4": "D"}   # everything else from check_call is "T"
RETRIEVAL = {"search_docs", "read_file", "query_db"}
_det: dict = {}

def detector():
    key = "qgate" if CFG["QGATE"] else "rbf"
    if key not in _det:
        from aegis.adapters import load_qgate, load_rbf
        _det[key] = load_qgate() if key == "qgate" else load_rbf()
    return _det[key]

_nli: dict = {}

def _nli_model():
    """H3 cross-encoder, loaded once per process (it is slow to load). None if unavailable.
    Keyed on the loader so tests that patch nli.load_model get their fake."""
    if _nli.get("loader") is not nli.load_model:
        try:
            model = nli.load_model()
        except Exception:
            model = None
        _nli.update(loader=nli.load_model, model=model)
    return _nli["model"]

def audit(state, event, **kw):
    if CFG["M"]:
        chain.log(event, state.session_id, **kw)

def _dump(vs):
    return [v.model_dump() for v in vs]

UNAVAILABLE = "The assistant is temporarily unavailable. Please try again."

# ---------------------------------------------------------------- entry points
def run_turn(state: SessionState, user_msg: str) -> TurnResult:
    """Never raises: any exception in any layer becomes a safe message (fail closed)."""
    try:
        return _run_turn(state, user_msg)
    except Exception as e:
        return _fail(state, e)

def resume(state: SessionState, approved: bool) -> TurnResult:
    """Continue after the human approved/denied state.pending. Never raises."""
    try:
        return _resume(state, approved)
    except Exception as e:
        return _fail(state, e)

def _repair(state):
    """Every assistant tool_call id needs a role:tool reply before the next LLM call, or the API errors."""
    answered = {m.get("tool_call_id") for m in state.messages if m["role"] == "tool"}
    for m in list(state.messages):
        for tc in m.get("tool_calls") or []:
            if tc["id"] not in answered:
                state.messages.append({"role": "tool", "tool_call_id": tc["id"], "content": "ERROR: internal error."})

def _fail(state, e) -> TurnResult:
    state.pending = None
    _repair(state)
    try:
        audit(state, "pipeline_error", error=type(e).__name__)
    except Exception:
        pass
    return TurnResult(answer=UNAVAILABLE, verdicts=[Verdict(layer="PIPELINE", decision="block", score=1,
                                                            reason=f"exception:{type(e).__name__}")])

def _run_turn(state: SessionState, user_msg: str) -> TurnResult:
    state.turn += 1
    state.retrieved = False
    verdicts: list[Verdict] = []
    if not state.messages:
        state.messages = [{"role": "system", "content": SYSTEM if CFG["J"] else BASELINE_SYSTEM}]
    if state.pending:                                              # user moved on without answering: deny
        call, state.pending = state.pending, None
        audit(state, "confirmation", tool=call.name, approved=False, reason="superseded")
        _tool_reply(state, call, "DENIED: the user did not approve this action.")
    state.pinned = state.pinned or list(TOOLS)
    if CFG["J"]:                                                   # steps 2-4: J1, J3, J5
        n = normalize(user_msg)
        j1 = classify.classify_input([n["normalized"], n["leet"], n["rot13"]], raw=user_msg)
        j3 = risk.update(state, j1)
        verdicts += [j1, j3]
        audit(state, "input", text_hash=chain.text_hash(user_msg), flags=n["flags"], verdicts=_dump(verdicts))
        if "refuse" in (j1.decision, j3.decision):
            return _done(state, REFUSAL, verdicts, refused=True)
    else:
        audit(state, "input", text_hash=chain.text_hash(user_msg), flags={}, verdicts=[])
    state.messages.append({"role": "user", "content": user_msg})
    return _loop(state, verdicts)

def _resume(state: SessionState, approved: bool) -> TurnResult:
    call, state.pending = state.pending, None
    if call is None:
        return TurnResult(answer="Nothing is waiting for approval.", verdicts=[])
    verdicts: list[Verdict] = []
    audit(state, "confirmation", tool=call.name, approved=approved)
    if approved:
        _run_tool(state, call, action_token.mint(call.name, call.args), verdicts)
    else:
        _tool_reply(state, call, "DENIED by the user. Do not retry.")
    return _loop(state, verdicts)

# ---------------------------------------------------------------- agent loop
def _loop(state, verdicts):
    for _ in range(MAX_STEPS):
        try:
            msg = llm.chat(state.messages, TOOL_SPECS)
        except Exception as e:                                     # fail closed, never crash the UI
            audit(state, "llm_error", error=type(e).__name__)
            return _done(state, UNAVAILABLE, verdicts)
        if not msg.tool_calls:
            return _finish(state, msg.content or "", verdicts)
        tcs = msg.tool_calls
        state.messages.append({"role": "assistant", "content": msg.content, "tool_calls": [
            {"id": t.id, "type": "function", "function": {"name": t.function.name, "arguments": t.function.arguments}}
            for t in tcs]})
        for extra in tcs[1:]:                                      # one call per step keeps gating simple
            state.messages.append({"role": "tool", "tool_call_id": extra.id, "content": "SKIPPED: call one tool at a time."})
        tc = tcs[0]
        try:
            args = json.loads(tc.function.arguments or "{}")
        except json.JSONDecodeError:
            args = {"_raw": tc.function.arguments}
        call = ToolCall(call_id=tc.id, name=tc.function.name, args=args)
        gate = _gate(state, call, verdicts)
        if gate.decision == "BLOCK":
            _tool_reply(state, call, "BLOCKED by policy.")
            continue
        if gate.decision == "CONFIRM":
            state.pending = call
            return TurnResult(answer=f"Approval needed for {call.name}: {json.dumps(call.args)}",
                              verdicts=verdicts, pending_confirmation=call)
        _run_tool(state, call, gate.token, verdicts)
    return _finish(state, "NOT_FOUND", verdicts)                  # step cap reached

def _gate(state, call, verdicts) -> GateDecision:
    tainted = [m["content"] for m in state.messages if m["role"] == "tool"]
    users = [m["content"] for m in state.messages if m["role"] == "user"]
    if CFG["LINE1"]:
        call.tainted_args = taint.mark(call.args, tainted, users)
    vs = [v for v in check_call(call, state, state.pinned) if CFG[GROUP.get(v.layer, "T")]]
    if (CFG["QGATE"] or CFG["CLASSICAL"]) and state.qgate_review and REGISTRY.get(call.name, {}).get("tier", 3) >= 2:
        vs.append(Verdict(layer="QGATE", decision="review", score=0.5, reason="session_flagged"))
    g = decide(call, vs)
    verdicts += g.verdicts
    audit(state, "tool_gate", tool=call.name, args_hash=action_token.action_hash(call.name, call.args),
          decision=g.decision, verdicts=_dump(g.verdicts))
    return g

def _run_tool(state, call, token, verdicts):
    state.tool_calls[call.name] = state.tool_calls.get(call.name, 0) + 1
    try:
        chunks = execute(call.name, call.args, token, enforce=CFG["LINE1"])
    except Exception as e:
        _tool_reply(state, call, f"ERROR: {type(e).__name__}")
        return
    state.retrieved |= call.name in RETRIEVAL
    parts = []
    for c in chunks:
        item, vs = process(c["text"], "doc" if call.name == "search_docs" else "tool", c["origin"], state, enabled=CFG["D"])
        if CFG["QGATE"] or CFG["CLASSICAL"]:
            q = detector().score(item.text)
            vs.append(q)
            if q.decision == "quarantine":
                item.text = "[QUARANTINED: possible injected instructions removed]"
            elif q.decision == "review":
                state.qgate_review = True
        verdicts += vs
        if not item.text.startswith("[QUARANTINED"):
            state.passages[item.id] = item
        parts.append(wrap(item.id, item.text) if CFG["J"] else f"[{item.id}] {item.text}")
        audit(state, "ingress", item=item.id, origin=item.origin, label=item.label,
              redactions=item.redactions, verdicts=_dump(vs))
    _tool_reply(state, call, "\n".join(parts) or "No results.")

def _tool_reply(state, call, text):
    state.messages.append({"role": "tool", "tool_call_id": call.call_id, "content": text})

# ---------------------------------------------------------------- output checker (step 16)
def _finish(state, text, verdicts):
    result = _check_output(state, text, verdicts)
    # history keeps what the user actually saw, so refused/redacted text can't resurface next turn
    state.messages.append({"role": "assistant", "content": result.answer})
    return result

def _check_output(state, text, verdicts):
    final = text
    if CFG["J"]:
        j4 = classify.classify_output(text)                         # J4 first
        verdicts.append(j4)
        if j4.decision == "refuse":
            return _done(state, REFUSAL, verdicts, refused=True)
    if CFG["D"]:
        if canary_hit(final):                                        # D3
            verdicts.append(Verdict(layer="D3", decision="block", score=1, reason="canary_leak"))
            return _done(state, REFUSAL, verdicts, refused=True)
        final, found = scan(final)                                   # D2
        if found:
            verdicts.append(Verdict(layer="D2", decision="redact", score=0.5, details={"types": found}))
        final = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", final)           # D4: no auto-loading images
    if CFG["H"] and (state.retrieved or "NOT_FOUND" in final):
        if "NOT_FOUND" in final:
            final = ABSTAIN
            verdicts.append(Verdict(layer="H5", decision="abstain", score=1))
        else:
            h2_checked = citation_check.check(final, state.passages)
            model = _nli_model()
            h3_checked = None
            if model is not None:
                try:
                    h3_checked = nli.check(h2_checked, state.passages, model=model)
                except Exception:
                    h3_checked = None
            if h3_checked is None:
                # H3 is a Recommended layer: if its model is missing or errors, fall back to the
                # deterministic H2 citation check instead of abstaining on every grounded answer.
                verdicts.append(Verdict(layer="H3", decision="flag", score=0.0, reason="nli_unavailable"))
                final, v = h5_decide(h2_checked)
                verdicts.append(v)
            else:
                rejected = sum(not item.get("supported", False)
                               for item in h3_checked)
                verdicts.append(Verdict(
                    layer="H3",
                    decision="prune" if rejected else "pass",
                    score=rejected / len(h3_checked) if h3_checked else 1.0,
                    details={"checked": len(h3_checked), "rejected": rejected},
                ))
                final, v = h5_decide(h3_checked, require_h3=True)
                verdicts.append(v)
    return _done(state, final, verdicts)

def _done(state, answer, verdicts, refused=False):
    audit(state, "output", answer_hash=chain.text_hash(answer), refused=refused, verdicts=_dump(verdicts))
    return TurnResult(answer=answer, verdicts=verdicts, refused=refused)
