"""D2: secret + PII scan and redaction. D3 canary check. Used on ingress and egress."""
import math, re
CANARIES = ["AEGIS-CANARY-7f3a9c", "sk-canary-0000DEADBEEF"]   # also planted in the system prompt and secret store

PATTERNS = {
    "AWS_KEY": r"\bAKIA[0-9A-Z]{16}\b",
    "API_KEY": r"\b(?:sk|pk|api|key)[-_][A-Za-z0-9_-]{16,}\b",
    "JWT": r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b",
    "PRIVATE_KEY": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "EMAIL": r"\b[\w.+-]+@[\w-]+\.[\w.]+\b",
    "PHONE": r"(?<!\d)(?:\+?\d{1,3}[ -]?)?\d{10}(?!\d)",
    "CARD": r"\b\d(?:[ -]?\d){12,15}\b",
    "AADHAAR": r"\b\d{4}\s\d{4}\s\d{4}\b",
}

def _luhn(num: str) -> bool:
    d = [int(c) for c in re.sub(r"\D", "", num)][::-1]
    return len(d) >= 13 and sum(x if i % 2 == 0 else (x * 2 - 9 if x * 2 > 9 else x * 2) for i, x in enumerate(d)) % 10 == 0

def _entropy(s: str) -> float:
    return -sum(s.count(c) / len(s) * math.log2(s.count(c) / len(s)) for c in set(s))

def scan(text: str, redact_emails: bool = False) -> tuple[str, list[str]]:
    """Returns (redacted_text, list_of_finding_types)."""
    found = []
    for kind, pat in PATTERNS.items():
        if kind == "EMAIL" and not redact_emails:
            continue
        def sub(m, kind=kind):
            if kind == "CARD" and not _luhn(m.group(0)):
                return m.group(0)
            found.append(kind)
            return f"[REDACTED:{kind}]"
        text = re.sub(pat, sub, text)
    # high-entropy tokens (unknown key formats)
    def ent(m):
        tok = m.group(0)
        if _entropy(tok) > 4.0 and any(c.isdigit() for c in tok) and any(c.isalpha() for c in tok):
            found.append("HIGH_ENTROPY"); return "[REDACTED:SECRET]"
        return tok
    text = re.sub(r"\b[A-Za-z0-9+/_-]{24,}\b", ent, text)
    return text, found

def canary_hit(text: str) -> bool:
    return any(c in text for c in CANARIES)
