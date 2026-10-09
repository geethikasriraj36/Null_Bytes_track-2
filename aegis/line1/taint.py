"""A2: mark which tool-call args were copied from untrusted content."""
import re
def _pieces(v: str) -> list[str]:
    # emails, URLs, and any 12+ char run are distinctive enough to trace
    return re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+|https?://\S+|\S{12,}", v)

def mark(args: dict, tainted_texts: list[str], user_texts: list[str]) -> list[str]:
    bad = []
    for k, v in args.items():
        for p in _pieces(str(v)):
            if any(p in t for t in tainted_texts) and not any(p in u for u in user_texts):
                bad.append(k); break
    return bad
