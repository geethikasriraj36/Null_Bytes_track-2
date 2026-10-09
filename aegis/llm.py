"""The ONLY place the team calls an LLM. Model pinned by env var; temperature 0."""
import json, os, re, time
import litellm
from aegis import trace

MODEL = os.environ.get("AEGIS_MODEL", "gpt-4o-mini")        # e.g. "anthropic/claude-...", "gemini/gemini-..."
JUDGE_MODEL = os.environ.get("AEGIS_JUDGE_MODEL", MODEL)
TIMEOUT = float(os.environ.get("AEGIS_LLM_TIMEOUT", "60"))
UNSAFE = {"label": "unsafe", "score": 1.0, "category": "judge_error"}   # fail-closed judge result

RATE_RETRIES = int(os.environ.get("AEGIS_RATE_RETRIES", "5"))   # waits ~5,10,20,40,60 s on HTTP 429

litellm.drop_params = True       # providers that reject an unknown param drop it instead of erroring
litellm.suppress_debug_info = True   # no "Give Feedback / Get Help" banner hiding the real error

LAST_ERROR = ""                  # most recent API failure, key-redacted; the eval prints it

def describe(e: Exception) -> str:
    """One readable line for an API failure, safe to print or log (API keys redacted)."""
    msg = re.sub(r"(gsk_|sk-|AIza)[\w-]+", r"\1<redacted>", str(e))
    m = re.search(r'"message"\s*:\s*"([^"]+)', msg)                # provider JSON error -> its message
    return f"{type(e).__name__}: {(m[1] if m else msg).strip()[:240]}"

def _note(e: Exception):
    global LAST_ERROR
    LAST_ERROR = describe(e)

def _retry_after(err) -> float:
    """Seconds the provider asks us to wait ('Please retry in 13h59m12.8s'); 0 if it doesn't say."""
    m = re.search(r"retry in (?:(\d+)h)?(?:(\d+)m)?([\d.]+)s", str(err))
    return int(m[1] or 0) * 3600 + int(m[2] or 0) * 60 + float(m[3]) if m else 0.0

def _complete(**kw):
    """litellm.completion, plus patient backoff on per-minute rate limits. A daily quota
    ('retry in 13h') fails at once: waiting would only freeze the UI or the eval."""
    for attempt in range(RATE_RETRIES + 1):
        try:
            return litellm.completion(**kw)
        except litellm.RateLimitError as e:
            wait = _retry_after(e) or min(60, 5 * 2 ** attempt)
            # Groq says "tokens per day (TPD) ... try again in 20s": a rolling DAILY window, not a
            # per-minute blip, so waiting just hangs the UI. Gemini says "quota ... retry in 13h".
            daily = re.search(r"per day|\b[TR]PD\b|quota", str(e), re.I)
            if attempt == RATE_RETRIES or wait > 120 or daily:
                raise
            time.sleep(wait)

def _traced(role: str, **kw):
    """_complete + one trace entry (model, latency, tokens) for the UI's stats panel."""
    t0 = time.perf_counter()
    try:
        r = _complete(**kw)
    except Exception as e:
        trace.llm_call(role, kw.get("model", ""), (time.perf_counter() - t0) * 1000, None, False, describe(e))
        raise
    usage = getattr(r, "usage", None)
    trace.llm_call(role, kw.get("model", ""), (time.perf_counter() - t0) * 1000,
                   getattr(usage, "total_tokens", None), True)
    return r

def chat(messages: list[dict], tools: list[dict] | None = None):
    """Returns the assistant message: .content (str|None) and .tool_calls (list|None).
    Raises on API failure after retries; pipeline._loop turns that into a safe message."""
    if MODEL == "mock":                                          # offline stand-in, see aegis/mockllm.py
        from aegis import mockllm
        trace.llm_call("agent", "mock (offline)", 0, None, True)
        return mockllm.chat(messages, tools)
    try:
        r = _traced("agent", model=MODEL, messages=messages, tools=tools or None,
                    temperature=0, num_retries=3, timeout=TIMEOUT)
    except Exception as e:
        _note(e)
        raise
    return r.choices[0].message

def _parse(raw: str) -> dict:
    """First {...} block in the reply -> {"label": str, "score": float 0-1, "category": str}."""
    j = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
    if not isinstance(j, dict) or "label" not in j:
        raise ValueError("judge reply has no label")
    return {"label": str(j["label"]).strip().lower(),
            "score": min(1.0, max(0.0, float(j.get("score", 1.0)))),
            "category": str(j.get("category", ""))[:60]}

def judge(system: str, text: str) -> dict:
    """Classifier-style call. Must return JSON; on ANY failure (API error, timeout, bad JSON)
    we fail CLOSED and report the text as unsafe."""
    if JUDGE_MODEL == "mock":
        from aegis import mockllm
        trace.llm_call("judge", "mock (offline)", 0, None, True)
        return mockllm.judge(system, text)
    # the text cannot close our delimiter and talk to the judge directly
    text = text.replace("</text>", "</ text>")
    try:
        r = _traced("judge", model=JUDGE_MODEL, temperature=0, num_retries=3, timeout=TIMEOUT / 2,
                    messages=[{"role": "system", "content": system},
                              {"role": "user", "content": f"<text>\n{text}\n</text>"}])
        return _parse(r.choices[0].message.content or "")
    except (ValueError, TypeError):
        return dict(UNSAFE, category="judge_parse_error")
    except Exception as e:                                       # network, auth, rate limit
        _note(e)
        return dict(UNSAFE, category=f"judge_api_error:{type(e).__name__}")
