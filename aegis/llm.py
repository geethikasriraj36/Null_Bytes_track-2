"""The ONLY place the team calls an LLM. Model pinned by env var; temperature 0."""
import json, os
import litellm

MODEL = os.environ.get("AEGIS_MODEL", "gpt-4o-mini")        # e.g. "anthropic/claude-...", "gemini/gemini-..."
JUDGE_MODEL = os.environ.get("AEGIS_JUDGE_MODEL", MODEL)

def chat(messages: list[dict], tools: list[dict] | None = None):
    """Returns the assistant message: .content (str|None) and .tool_calls (list|None)."""
    r = litellm.completion(model=MODEL, messages=messages, tools=tools or None,
                           temperature=0, num_retries=3, timeout=60)
    return r.choices[0].message

def judge(system: str, text: str) -> dict:
    """Classifier-style call. Must return JSON; on any parse error we fail CLOSED (unsafe)."""
    r = litellm.completion(model=JUDGE_MODEL, temperature=0, num_retries=3, timeout=30,
                           messages=[{"role": "system", "content": system},
                                     {"role": "user", "content": f"<text>\n{text}\n</text>"}])
    raw = r.choices[0].message.content or ""
    try:
        return json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
    except ValueError:
        return {"label": "unsafe", "score": 1.0, "category": "judge_parse_error"}
