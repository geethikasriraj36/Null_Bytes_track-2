"""Chainlit UI. Run: chainlit run app.py -w      (no -w on stage)
Shows the answer, an 'Aegis layers' step listing every verdict that fired, and Approve/Deny buttons for CONFIRM."""
import json, os, uuid
from pathlib import Path
import chainlit as cl
from aegis import pipeline
from aegis.config import CFG
from aegis.contracts import SessionState

CONFIG_NAME = Path(os.environ.get("AEGIS_CONFIG", "default")).stem
IS_BASELINE = not any(CFG.values()) or CONFIG_NAME.startswith("0_")

LAYER = {"J1": "Jailbreak classifier", "J3": "Multi-turn risk", "J4": "Output moderation",
         "A1": "Tool pinning", "A2": "Taint: untrusted data in a sensitive argument", "A3": "Memory guard",
         "T1": "Tool registry", "T2": "Argument validation", "T4": "Human confirmation", "T6": "Rate limit",
         "T7": "Data-flow (lethal trifecta)", "D1": "Access control", "D2": "Secret/PII redaction",
         "D3": "Canary leak", "D4": "Egress allowlist", "QGATE": "Q-Gate (quantum kernel)",
         "RBF": "Classical RBF detector", "H5": "Grounding / citations", "PIPELINE": "Fail-closed"}
ICON = {"block": "⛔ BLOCK", "refuse": "⛔ REFUSE", "confirm": "✋ CONFIRM", "review": "⚠️ REVIEW",
        "quarantine": "🧪 QUARANTINE", "redact": "✂️ REDACT", "strict": "⚠️ STRICT", "flag": "⚠️ FLAG",
        "prune": "✂️ PRUNE", "abstain": "🤐 ABSTAIN"}

def layer_table(verdicts) -> str:
    hits = [v for v in verdicts if v.decision not in ("pass", "allow")]
    passed = len(verdicts) - len(hits)
    if not hits:
        return f"All {passed} checks passed."
    rows = "\n".join(f"| {ICON.get(v.decision, v.decision)} | **{v.layer}** {LAYER.get(v.layer, '')} "
                     f"| {v.score:.2f} | {v.reason or ''} |" for v in hits)
    return f"| Decision | Layer | Score | Reason |\n|---|---|---|---|\n{rows}\n\n{passed} other checks passed."

async def show(res):
    if res.verdicts:
        async with cl.Step(name="Aegis layers", type="tool") as step:
            step.output = layer_table(res.verdicts)
    await cl.Message(content=res.answer).send()

async def handle(res, state):
    while res.pending_confirmation:
        c = res.pending_confirmation
        if res.verdicts:
            async with cl.Step(name="Aegis layers", type="tool") as step:
                step.output = layer_table(res.verdicts)
        ask = await cl.AskActionMessage(
            content=f"Aegis needs your approval before running **{c.name}**:\n"
                    f"```json\n{json.dumps(c.args, indent=2)}\n```",
            actions=[cl.Action(name="approve", payload={"ok": True}, label="Approve"),
                     cl.Action(name="deny", payload={"ok": False}, label="Deny")], timeout=300).send()
        ok = bool(ask and (ask.get("payload") or {}).get("ok"))
        await cl.Message(content="Approved by you." if ok else "Denied.", author="Aegis").send()
        res = await cl.make_async(pipeline.resume)(state, ok)
    await show(res)

@cl.on_chat_start
async def start():
    cl.user_session.set("state", SessionState(session_id=uuid.uuid4().hex[:12]))
    mode = "BASELINE (no defenses)" if IS_BASELINE else "Aegis ON"
    on = ", ".join(k for k, v in CFG.items() if v) or "none"
    await cl.Message(content=f"**{mode}** · config `{CONFIG_NAME}` · layers on: {on}\n\n"
                             "Ask about company documents, or try to break me.").send()

@cl.on_message
async def on_message(msg: cl.Message):
    state = cl.user_session.get("state")
    res = await cl.make_async(pipeline.run_turn)(state, msg.content)
    await handle(res, state)
