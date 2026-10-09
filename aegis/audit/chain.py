"""M1-M3: append-only, hash-chained JSONL audit log."""
import hashlib, json, time, uuid, os, threading
from pathlib import Path

LOG = Path(os.environ.get("AEGIS_AUDIT", "logs/audit.jsonl"))
GENESIS = "0" * 64
_lock = threading.Lock()          # the eval runner logs from several threads

def _h(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

def _last_hash() -> str:
    if not LOG.exists() or LOG.stat().st_size == 0:
        return GENESIS
    with LOG.open("rb") as f:
        last = f.readlines()[-1]
    return json.loads(last)["hash"]

def log(event: str, session_id: str, **fields) -> dict:
    """Append one record. Never pass raw secrets: hash or redact first (M3)."""
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        rec = {"event_id": uuid.uuid4().hex, "ts": time.time(), "event": event,
               "session": session_id, **fields, "prev": _last_hash()}
        rec["hash"] = _h(json.dumps(rec, sort_keys=True, default=str))
        with LOG.open("a") as f:
            f.write(json.dumps(rec, sort_keys=True, default=str) + "\n")
    return rec

def verify_chain(path: Path = LOG) -> tuple[bool, int | None]:
    """Returns (ok, first_bad_line). Detects edits, deletions, reorders."""
    prev = GENESIS
    for i, line in enumerate(path.read_text().splitlines(), 1):
        rec = json.loads(line)
        h = rec.pop("hash")
        if rec["prev"] != prev or _h(json.dumps(rec, sort_keys=True, default=str)) != h:
            return False, i
        prev = h
    return True, None

def text_hash(s: str) -> str:
    return _h(s)[:16]
