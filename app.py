"""Chainlit UI. Run: chainlit run app.py -w
Shows the answer, a 'Layers' step listing every non-pass verdict, and Approve/Deny buttons for CONFIRM."""
import json, uuid
import chainlit as cl
from aegis import pipeline
from aegis.contracts import SessionState

ICON = {"block": "BLOCK", "refuse": "REFUSE", "confirm": "CONFIRM", "review": "REVIEW",
        "quarantine": "QUARANTINE", "redact": "REDACT", "strict": "STRICT", "flag": "FLAG",
        "prune": "PRUNE", "abstain": "ABSTAIN"}

async def show(res):
    hits = [v for v in res.verdicts if v.decision not in ("pass", "allow")]
    if hits:
        async with cl.Step(name="Aegis layers") as step:
            step.output = "\n".join(f"{ICON.get(v.decision, v.decision)}  {v.layer}  score={v.score:.2f}  {v.reason}"
                                    for v in hits)
    await cl.Message(content=res.answer).send()

async def handle(res, state):
    while res.pending_confirmation:
        c = res.pending_confirmation
        ask = await cl.AskActionMessage(
            content=f"Aegis needs your approval:\n```json\n{json.dumps({'tool': c.name, 'args': c.args}, indent=2)}\n```",
            actions=[cl.Action(name="approve", payload={"ok": True}, label="Approve"),
                     cl.Action(name="deny", payload={"ok": False}, label="Deny")], timeout=300).send()
        ok = bool(ask and ask.get("payload", {}).get("ok"))
        res = await cl.make_async(pipeline.resume)(state, ok)
    await show(res)

@cl.on_chat_start
async def start():
    cl.user_session.set("state", SessionState(session_id=uuid.uuid4().hex[:12]))
    await cl.Message(content="Aegis Assistant ready. Ask about company documents, or try to break me.").send()

@cl.on_message
async def on_message(msg: cl.Message):
    state = cl.user_session.get("state")
    res = await cl.make_async(pipeline.run_turn)(state, msg.content)
    await handle(res, state)
