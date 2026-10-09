"""Aegis web UI server (M1). Replaces the Chainlit UI for the demo; same pipeline underneath.
Run:  python -m web.server            then open http://localhost:8000
Each chat has its own config (the "model picker" = the ablation switch). One request at a time,
because layer flags (aegis.config.CFG) are process-wide."""
import json
import os
import threading
import time
import uuid
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from aegis import config, llm, pipeline
from aegis.audit import chain
from aegis.contracts import SessionState

ROOT = Path(__file__).resolve().parents[1]
STATIC = Path(__file__).resolve().parent / "static"
os.chdir(ROOT)                                       # tools read data/ relative to the repo root
chain.LOG = Path(os.environ.get("AEGIS_AUDIT", "logs/audit.jsonl"))

CONFIGS = {   # id -> (picker name, one-line description)
    "7_full":            ("Aegis · Full protection", "every layer on"),
    "6_plus_t":          ("Aegis · no fact-check", "all but H1-H5 grounding checks"),
    "5_plus_d":          ("Aegis · no tool limits", "Line 1, Q-Gate, jailbreak guard, data protection"),
    "4_plus_j":          ("Line 1 + Q-Gate + jailbreak guard", "no data protection, no tool limits"),
    "2_line1_qgate":     ("Line 1 + Q-Gate", "deterministic rules + quantum detector"),
    "3_line1_classical": ("Line 1 + classical twin", "deterministic rules + RBF detector"),
    "1_line1":           ("Line 1 only", "deterministic action rules"),
    "0_baseline":        ("Baseline · no protection", "the plain agent, for comparison"),
}
CHATS: dict[str, dict] = {}
LOCK = threading.Lock()
# chats survive a server restart; one file per port so two servers (e.g. demo + baseline) never clash
STORE = Path(os.environ.get("AEGIS_CHATS", f"logs/chats_{os.environ.get('AEGIS_PORT', '8000')}.json"))
app = FastAPI(title="Aegis")


def _save():
    """Write all chats (including each SessionState) to STORE atomically."""
    data = {cid: {**{k: v for k, v in c.items() if k != "state"}, "state": c["state"].model_dump(mode="json")}
            for cid, c in CHATS.items()}
    STORE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STORE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, default=str), encoding="utf-8")
    tmp.replace(STORE)


def _load():
    if not STORE.exists():
        return
    try:
        for cid, c in json.loads(STORE.read_text(encoding="utf-8")).items():
            CHATS[cid] = {**c, "state": SessionState.model_validate(c["state"])}
    except Exception as e:                       # a corrupt file must never stop the demo from starting
        print(f"could not load saved chats ({type(e).__name__}); starting fresh")


@app.middleware("http")
async def no_stale_ui(request, call_next):
    """Always revalidate the UI files, so an edited app.js is never served from a stale browser cache."""
    resp = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static/"):
        resp.headers["Cache-Control"] = "no-cache"
    return resp


class NewChat(BaseModel):
    config: str = "7_full"

class Message(BaseModel):
    text: str

class Decision(BaseModel):
    approved: bool

class SetConfig(BaseModel):
    config: str


def _flags(cfg_id: str) -> dict:
    import yaml
    return {**config.DEFAULT, **yaml.safe_load((ROOT / "configs" / f"{cfg_id}.yaml").read_text())}

def _needs_model(cfg_id: str) -> str | None:
    f = _flags(cfg_id)
    if f.get("QGATE") and not Path("models/qgate.pkl").exists():
        return "models/qgate.pkl missing: run python -m scripts.train_qgate"
    if f.get("CLASSICAL") and not f.get("QGATE") and not Path("models/rbf.pkl").exists():
        return "models/rbf.pkl missing: run python -m scripts.train_qgate"
    return None

def _chat(chat_id: str) -> dict:
    if chat_id not in CHATS:
        raise HTTPException(404, "no such chat")
    return CHATS[chat_id]

def _summary(c: dict) -> dict:
    return {"id": c["id"], "title": c["title"], "config": c["config"], "created": c["created"],
            "updated": c["updated"], "pending": c["state"].pending is not None}

def _audit_status() -> dict:
    if not chain.LOG.exists():
        return {"records": 0, "valid": True, "head": ""}
    lines = [l for l in chain.LOG.read_text(encoding="utf-8").splitlines() if l.strip()]
    res = chain.verify_chain(chain.LOG)
    head = json.loads(lines[-1]).get("hash", "") if lines else ""
    return {"records": len(lines), "valid": res["valid"], "error": res.get("error"), "head": head[:12]}

def _run(c: dict, fn, *args) -> dict:
    """Runs one pipeline call under this chat's config; returns the stored result item."""
    problem = _needs_model(c["config"])
    if problem:
        raise HTTPException(409, problem)
    with LOCK:
        config.use(ROOT / "configs" / f"{c['config']}.yaml")
        res = fn(c["state"], *args)
        status = _audit_status() if res.trace.get("audit_records") else None
    st = c["state"]
    item = {
        "kind": "result", "ts": time.time(), "answer": res.answer, "refused": res.refused,
        "pending": res.pending_confirmation.model_dump() if res.pending_confirmation else None,
        "verdicts": [v.model_dump() for v in res.verdicts], "trace": res.trace, "audit": status,
        "sources": {pid: p.origin for pid, p in st.passages.items()},
        "unavailable": res.answer == pipeline.UNAVAILABLE,
        "last_error": llm.LAST_ERROR if res.answer == pipeline.UNAVAILABLE else "",
    }
    c["items"].append(item)
    c["updated"] = time.time()
    return item


# ---------------------------------------------------------------- API
@app.get("/api/meta")
def meta():
    return {"configs": [{"id": k, "name": n, "desc": d, "flags": _flags(k), "unavailable": _needs_model(k)}
                        for k, (n, d) in CONFIGS.items()],
            "model": llm.MODEL, "judge": llm.JUDGE_MODEL, "default": "7_full"}

@app.get("/api/chats")
def list_chats():
    return sorted((_summary(c) for c in CHATS.values()), key=lambda c: -c["updated"])

@app.post("/api/chats")
def new_chat(body: NewChat):
    if body.config not in CONFIGS:
        raise HTTPException(400, "unknown config")
    cid = uuid.uuid4().hex[:10]
    now = time.time()
    CHATS[cid] = {"id": cid, "title": "New chat", "config": body.config, "created": now, "updated": now,
                  "state": SessionState(session_id=f"ui-{cid}"), "items": []}
    _save()
    return _summary(CHATS[cid])

@app.get("/api/chats/{chat_id}")
def get_chat(chat_id: str):
    c = _chat(chat_id)
    return {**_summary(c), "items": c["items"]}

@app.delete("/api/chats/{chat_id}")
def delete_chat(chat_id: str):
    CHATS.pop(chat_id, None)
    _save()
    return {"ok": True}

@app.post("/api/chats/{chat_id}/config")
def set_config(chat_id: str, body: SetConfig):
    c = _chat(chat_id)
    if body.config not in CONFIGS:
        raise HTTPException(400, "unknown config")
    if c["items"]:
        raise HTTPException(409, "chat already started; open a new chat to switch protection")
    c["config"] = body.config
    _save()
    return _summary(c)

@app.post("/api/chats/{chat_id}/message")
def send(chat_id: str, body: Message):
    c = _chat(chat_id)
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "empty message")
    if c["title"] == "New chat":
        c["title"] = text[:42] + ("…" if len(text) > 42 else "")
    user = {"kind": "user", "ts": time.time(), "text": text}
    c["items"].append(user)
    try:
        return {"items": [user, _run(c, pipeline.run_turn, text)], "chat": _summary(c)}
    finally:
        _save()

@app.post("/api/chats/{chat_id}/resume")
def decide(chat_id: str, body: Decision):
    c = _chat(chat_id)
    if c["state"].pending is None:
        raise HTTPException(409, "nothing is waiting for approval")
    note = {"kind": "decision", "ts": time.time(), "approved": body.approved, "tool": c["state"].pending.name}
    c["items"].append(note)
    try:
        return {"items": [note, _run(c, pipeline.resume, body.approved)], "chat": _summary(c)}
    finally:
        _save()

@app.get("/api/audit")
def audit(limit: int = 60):
    status = _audit_status()
    rows = []
    if chain.LOG.exists():
        for line in chain.LOG.read_text(encoding="utf-8").splitlines()[-limit:]:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                rows.append({"broken": line[:80]})
                continue
            ev = r.get("event", {})
            rows.append({"seq": r.get("sequence"), "ts": r.get("timestamp"), "event": ev.get("event"),
                         "session": ev.get("session"), "decision": ev.get("decision") or ev.get("tool") or "",
                         "prev": str(r.get("previous_hash", ""))[:10], "hash": str(r.get("hash", ""))[:10]})
    return {"path": str(chain.LOG), **status, "rows": rows}

@app.get("/api/results")
def results():
    out = {"qgate": None, "tuning": None, "summary": [], "images": []}
    rd = Path("results")
    if (rd / "qgate_e1_e2.json").exists():
        out["qgate"] = json.loads((rd / "qgate_e1_e2.json").read_text())
    if (rd / "qgate_tuning.json").exists():
        out["tuning"] = json.loads((rd / "qgate_tuning.json").read_text())
    if (rd / "summary.csv").exists():
        import csv
        out["summary"] = list(csv.DictReader((rd / "summary.csv").open(encoding="utf-8")))
    out["images"] = sorted(p.name for p in rd.glob("*.png")) if rd.exists() else []
    return out


_load()
Path("results").mkdir(exist_ok=True)
app.mount("/results", StaticFiles(directory="results"), name="results")
app.mount("/static", StaticFiles(directory=STATIC), name="static")

@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


if __name__ == "__main__":
    port = int(os.environ.get("AEGIS_PORT", "8000"))
    print(f"Aegis UI on http://localhost:{port}   (model {llm.MODEL}, judge {llm.JUDGE_MODEL})")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
