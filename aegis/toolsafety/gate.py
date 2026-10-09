"""Tool Safety Gate (T1, T2, T4 triggers, T6, T7, D4) + A2 taint policy + action gate."""
import yaml
from pathlib import Path
from aegis.contracts import ToolCall, SessionState, Verdict, GateDecision
from aegis.toolsafety.validate import validate
from aegis.line1 import action_token

POL = Path(__file__).resolve().parent.parent / "policy"
REGISTRY = yaml.safe_load((POL / "tool_registry.yaml").read_text())
ALLOW = yaml.safe_load((POL / "egress_allowlist.yaml").read_text())
MAX_CALLS = {"default": 8, "send_email": 2}

def check_call(call: ToolCall, state: SessionState, pinned: list[str]) -> list[Verdict]:
    v: list[Verdict] = []
    spec = REGISTRY.get(call.name)
    # T1 registry + A1 pinning
    if spec is None:
        return [Verdict(layer="T1", decision="block", score=1, reason="unregistered_tool")]
    if call.name not in pinned:
        v.append(Verdict(layer="A1", decision="block", score=1, reason="tool_not_pinned"))
    # T2 argument validation
    err = validate(call.name, call.args)
    if err:
        v.append(Verdict(layer="T2", decision="block", score=1, reason="bad_args", details={"error": err}))
    # D4 egress allowlist
    if spec.get("egress_arg"):
        dest = str(call.args.get(spec["egress_arg"], ""))
        if dest.split("@")[-1].lower() not in ALLOW["email_domains"]:
            v.append(Verdict(layer="D4", decision="block", score=1, reason="egress_not_allowlisted"))
    # A2 taint: tainted values may not fill sensitive args
    bad = set(call.tainted_args) & set(spec.get("sensitive_args", []))
    if bad and spec["tier"] >= 2:
        v.append(Verdict(layer="A2", decision="block", score=1, reason="tainted_sensitive_arg", details={"args": sorted(bad)}))
    # T6 limits
    n = state.tool_calls.get(call.name, 0)
    if n >= MAX_CALLS.get(call.name, MAX_CALLS["default"]):
        v.append(Verdict(layer="T6", decision="block", score=1, reason="call_limit"))
    # T7 data-flow: private + untrusted + external send in one session
    if spec["tier"] == 3 and state.seen_private and state.seen_tainted:
        v.append(Verdict(layer="T7", decision="confirm", score=0.7, reason="lethal_trifecta"))
    # T4 confirmation triggers
    if spec["tier"] == 3:
        v.append(Verdict(layer="T4", decision="confirm", score=0.5, reason="tier3"))
    elif spec["tier"] == 2 and (call.tainted_args or state.strict):
        v.append(Verdict(layer="T4", decision="confirm", score=0.5, reason="tier2_tainted_or_strict"))
    if not v:
        v.append(Verdict(layer="T", decision="allow", score=0))
    return v

def decide(call: ToolCall, verdicts: list[Verdict]) -> GateDecision:
    """Action gate. Deterministic BLOCK always wins; advisory layers can only escalate to CONFIRM."""
    deterministic = {"T1", "T2", "A1", "A2", "A3", "D4", "T6"}
    if any(x.decision == "block" and x.layer in deterministic for x in verdicts):
        return GateDecision(decision="BLOCK", verdicts=verdicts)
    if any(x.decision in ("confirm", "review", "quarantine", "block") for x in verdicts):
        return GateDecision(decision="CONFIRM", verdicts=verdicts)
    return GateDecision(decision="ALLOW", verdicts=verdicts, token=action_token.mint(call.name, call.args))
