"""The ONLY place the team calls an LLM. Model pinned by env var; temperature 0."""
import json, os
import litellm

MODEL = os.environ.get("AEGIS_MODEL", "gpt-4o-mini")        # e.g. "anthropic/claude-...", "gemini/gemini-..."
JUDGE_MODEL = os.environ.get("AEGIS_JUDGE_MODEL", MODEL)
TIMEOUT = float(os.environ.get("AEGIS_LLM_TIMEOUT", "60"))
UNSAFE = {"label": "unsafe", "score": 1.0, "category": "judge_error"}   # fail-closed judge result

litellm.drop_params = True       # providers that reject an unknown param drop it instead of erroring

def chat(messages: list[dict], tools: list[dict] | None = None):
    """Returns the assistant message: .content (str|None) and .tool_calls (list|None).
    Raises on API failure after 3 retries; pipeline._loop turns that into a safe message."""
    r = litellm.completion(model=MODEL, messages=messages, tools=tools or None,
                           temperature=0, num_retries=3, timeout=TIMEOUT)
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
    # the text cannot close our delimiter and talk to the judge directly
    text = text.replace("</text>", "</ text>")
    try:
        r = litellm.completion(model=JUDGE_MODEL, temperature=0, num_retries=3, timeout=TIMEOUT / 2,
                               messages=[{"role": "system", "content": system},
                                         {"role": "user", "content": f"<text>\n{text}\n</text>"}])
        return _parse(r.choices[0].message.content or "")
    except (ValueError, TypeError):
        return dict(UNSAFE, category="judge_parse_error")
    except Exception as e:                                       # network, auth, rate limit
        return dict(UNSAFE, category=f"judge_api_error:{type(e).__name__}")
