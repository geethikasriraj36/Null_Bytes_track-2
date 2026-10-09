
import re
import math
from collections import Counter
from typing import Iterable


# Demo canaries: use synthetic values only, never real credentials.
CANARIES = {
    "AEGIS_CANARY_7F3A91",
    "AEGIS_SECRET_CANARY_C92D14",
}


PATTERNS = {
    "email": re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    ),
    "phone": re.compile(
        r"(?<!\w)(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}(?!\w)"
    ),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "generic_secret": re.compile(
        r"(?i)\b(?:api[_-]?key|access[_-]?token|secret|password)"
        r"\s*[:=]\s*['\"]?[A-Za-z0-9_\-./+=]{8,}['\"]?"
    ),
    "ipv4": re.compile(
        r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
    ),
}


def _entropy(value: str) -> float:
    """Shannon character entropy; useful as one secret-detection signal."""
    if not value:
        return 0.0

    counts = Counter(value)
    length = len(value)

    return -sum(
        (count / length) * math.log2(count / length)
        for count in counts.values()
    )


def _luhn_valid(value: str) -> bool:
    """Return True if a digit string passes the Luhn checksum."""
    digits = [int(char) for char in value if char.isdigit()]

    if not 13 <= len(digits) <= 19:
        return False

    total = 0
    parity = len(digits) % 2

    for index, digit in enumerate(digits):
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit

    return total % 10 == 0


def scan(text: str) -> dict:
    """
    Scan text for known secret/PII patterns.

    Returns:
        {
            "matches": [{"type": ..., "value": ..., "start": ..., "end": ...}],
            "canary_hits": [...]
        }
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    matches = []

    for category, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            matches.append({
                "type": category,
                "value": match.group(0),
                "start": match.start(),
                "end": match.end(),
            })

    # Credit-card-like digit sequences: require a valid Luhn checksum.
    for match in re.finditer(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)", text):
        candidate = match.group(0)

        if _luhn_valid(candidate):
            matches.append({
                "type": "payment_card",
                "value": candidate,
                "start": match.start(),
                "end": match.end(),
            })

    # High-entropy tokens are only flagged when they are sufficiently long
    # and contain mixed character classes, reducing indiscriminate matches.
    for match in re.finditer(r"\b[A-Za-z0-9_+/=-]{20,}\b", text):
        token = match.group(0)

        has_letters = bool(re.search(r"[A-Za-z]", token))
        has_digits = bool(re.search(r"\d", token))

        if has_letters and has_digits and _entropy(token) >= 3.5:
            matches.append({
                "type": "high_entropy_token",
                "value": token,
                "start": match.start(),
                "end": match.end(),
            })

    # Remove exact duplicate spans/categories, then order by text position.
    unique = {
        (item["type"], item["start"], item["end"]): item
        for item in matches
    }

    return {
        "matches": sorted(
            unique.values(),
            key=lambda item: (item["start"], item["end"]),
        ),
        "canary_hits": canary_hit(text),
    }


def canary_hit(text: str) -> list[str]:
    """Return any known canary tokens found in text."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    return sorted(token for token in CANARIES if token in text)



def redact(text: str, replacement: str = "[REDACTED]") -> str:
    """Redact sensitive values and canary tokens."""
    matches = scan(text)["matches"]
    spans = [(m["start"], m["end"]) for m in matches]

    # Include canary tokens in redaction.
    for token in CANARIES:
        start = 0
        while True:
            start = text.find(token, start)
            if start == -1:
                break
            spans.append((start, start + len(token)))
            start += len(token)

    # Replace from right to left to preserve character positions.
    for start, end in sorted(set(spans), reverse=True):
        text = text[:start] + replacement + text[end:]

    return text