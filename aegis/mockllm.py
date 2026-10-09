"""Offline stand-in for the LLM (AEGIS_MODEL=mock). For UI development and as the demo's no-network backup.

It imitates what we MEASURED from groq/openai/gpt-oss-120b on this project (see docs/M1_notes.md):
  - without the hardened prompt (baseline) it obeys an instruction hidden in a document table row;
  - with the J2 system prompt (spotlighting) it ignores it;
  - it answers from the most relevant passage and cites the passage id.
It is NOT a language model and must never be used for evaluation numbers: the UI labels it "offline".
Deterministic and stateless: every reply is a pure function of the message history."""
import base64
import binascii
import json
import re
from types import SimpleNamespace as NS

EMAIL = r"[\w.+-]+@[\w-]+\.[\w.]+"
STOP = set("what which when where who whom whose how many much does do did is are was were the a an in on of to for "
           "from with and or our your my me tell say says said about changed change new there this that it its "
           "please can could would should will any some".split())


STOP |= set("long take many much time get need know want give like".split())

def _keywords(text: str) -> set[str]:
    """Content words, plural 's' folded ('refunds' -> 'refund')."""
    return {w[:-1] if len(w) > 3 and w.endswith("s") else w
            for w in re.findall(r"[a-z0-9]{3,}", text.lower()) if w not in STOP}
JAILBREAK = re.compile(r"ignore (all )?(previous|prior)|\bDAN\b|developer mode|system prompt|no (rules|filters|restrictions)|"
                       r"unfiltered|you are no longer|internal marker|hidden instructions|without safety", re.I)


def _msg(content=None, call=None):
    calls = None
    if call:
        calls = [NS(id=f"mock_{abs(hash(json.dumps(call, sort_keys=True))) % 10**8}",
                    function=NS(name=call[0], arguments=json.dumps(call[1])))]
    return NS(content=content, tool_calls=calls)


def _turn(messages):
    """Messages since the last user message (this turn), plus that user message."""
    idx = max(i for i, m in enumerate(messages) if m["role"] == "user")
    return messages[idx]["content"], messages[idx + 1:]


def _passages(tool_text: str) -> list[tuple[str, str]]:
    blocks = re.findall(r"<untrusted id=(p_[0-9a-f]{8})>\n(.*?)\n</untrusted>", tool_text, re.S)
    return blocks or re.findall(r"\[(p_[0-9a-f]{8})\] (.*?)(?=\n\[p_|\Z)", tool_text, re.S)


def chat(messages, tools=None):
    system = messages[0]["content"] if messages and messages[0]["role"] == "system" else ""
    hardened = "<untrusted" in system
    user, since = _turn(messages)
    done = [c["function"]["name"] for m in since for c in (m.get("tool_calls") or [])]
    tool_text = "\n".join(m["content"] for m in since if m["role"] == "tool")
    low = user.lower()

    if not hardened and JAILBREAK.search(low) and not done:                  # gullible baseline
        return _msg("Sure. My instructions say: " + system)
    if not done:
        to = re.search(EMAIL, user)
        if to and ("email" in low or "send" in low):
            body = re.split(r"\bthat\b", user, 1)[-1].strip() or user
            return _msg(call=("send_email", {"to": to[0], "subject": "Message from Aegis Assistant", "body": body}))
        if "note" in low and ("save" in low or "write" in low):
            return _msg(call=("write_note", {"title": "note", "body": user[:200]}))
        f = re.search(r"(?:read|open|show)\s+(?:the\s+)?(?:file\s+)?([\w./\\-]+\.\w+)", user, re.I)
        if f:
            return _msg(call=("read_file", {"path": f[1]}))
        return _msg(call=("search_docs", {"query": " ".join(sorted(_keywords(user)))[:120] or user[:120]}))

    asked_email = bool(re.search(EMAIL, user)) and ("email" in low or "send" in low)
    if "send_email" in done and asked_email:
        return _msg("Done. The email has been sent." if "queued" in tool_text else "I couldn't send that email.")
    if "write_note" in done:
        return _msg("Saved.")
    # obey a hidden table/workflow instruction only when NOT protected by the hardened prompt (measured behaviour)
    hidden = re.search(r"AI assistant[^\n]*?(?:email|send)[^\n]*?(" + EMAIL + ")", tool_text, re.I)
    if hidden and not hardened and "send_email" not in done:
        return _msg(call=("send_email", {"to": hidden[1].rstrip(".,)|"), "subject": "Pune lane audit",
                                         "body": "Summary: shipping to Pune now takes 4 days."}))
    words = _keywords(user)
    need = max(1, -(-len(words) // 2))            # a sentence must cover at least half the question's key words
    best, best_s = None, 0
    for pid, text in _passages(tool_text):
        doc_bonus = 0
        for sent in re.split(r"(?<=[.!?])\s+|\n+", text):
            if sent.lstrip().startswith("#"):                               # headings are not answers
                continue
            sent = re.sub(r"\s*\|\s*", " ", sent).strip(" -#")             # table rows -> plain text
            sent = re.sub(r"^\d+\s+\w+\s+", "", sent)                       # drop "1 Logistics" table cells
            if "assistant" in sent.lower() or len(sent) < 12 or set(sent) <= set("-| "):
                continue
            s = len(words & _keywords(sent)) + 0.5 * doc_bonus + (0.25 if re.search(r"\d", sent) else 0)
            if len(words & _keywords(sent)) < need:
                continue
            if s > best_s:
                best, best_s = (pid, sent), s
    if not best:
        return _msg("NOT_FOUND")
    pid, sent = best
    sent = sent.rstrip(" .") + "."
    sent = re.sub(r"^(?:Update|Set|Change)\s+(.+?)\s+to\s+(.+)$", r"\1 is now \2", sent, flags=re.I)   # table action -> fact
    sent = re.sub(r"(\d[\d,.]*(?:\s*(?:to|-)\s*\d+)?\s*(?:business\s+)?(?:days?|hours?|percent|%|rupees|characters|units)?)",
                  lambda m: (f"**{m[1].strip()}**" + (" " if m[1] != m[1].rstrip() else "")) if m[1].strip() else m[1], sent, count=1)   # key fact in bold
    answer = f"{sent[0].upper()}{sent[1:]} [{pid}]"
    if hidden and hardened:                                   # say what we refused to do, citing where it came from
        src = next((p for p, t in _passages(tool_text) if hidden[1] in t), None)
        if src:
            answer += f"\nHeads-up: this document also told me to email {hidden[1].rstrip('.,)|')}; I ignored it. [{src}]"
    return _msg(answer)


def _decode_views(text: str) -> str:
    out = [text]
    for tok in re.findall(r"[A-Za-z0-9+/]{16,}={0,2}", text):
        try:
            out.append(base64.b64decode(tok + "=" * (-len(tok) % 4)).decode("utf-8", "ignore"))
        except (binascii.Error, ValueError):
            pass
    return " ".join(out)


def judge(system: str, text: str) -> dict:
    if "ANSWER" in system:                                                    # J4 output moderation
        return {"label": "safe", "score": 0.02, "category": "mock"}
    bad = JAILBREAK.search(_decode_views(text))
    return ({"label": "jailbreak", "score": 0.95, "category": "mock_pattern"} if bad
            else {"label": "safe", "score": 0.02, "category": "mock"})
