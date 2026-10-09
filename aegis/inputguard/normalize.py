"""J1 step 1: undo common obfuscation before classifying."""
import base64, binascii, codecs, re, unicodedata

ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍⁠﻿­"), None)
LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})
B64 = re.compile(r"\b[A-Za-z0-9+/]{16,}={0,2}")
HEX = re.compile(r"\b(?:[0-9a-fA-F]{2}){8,}\b")

def _try_b64(m):
    try:
        out = base64.b64decode(m.group(0), validate=True).decode("utf-8")
        return out if out.isprintable() else m.group(0)
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return m.group(0)

def _try_hex(m):
    try:
        out = bytes.fromhex(m.group(0)).decode("utf-8")
        return out if out.isprintable() else m.group(0)
    except (ValueError, UnicodeDecodeError):
        return m.group(0)

def normalize(text: str) -> dict:
    """Returns the views the classifier should see, plus flags for the audit log."""
    t = text.translate(ZERO_WIDTH)
    t = unicodedata.normalize("NFKC", t)          # folds full-width and many homoglyphs
    decoded = HEX.sub(_try_hex, B64.sub(_try_b64, t))
    rot = codecs.decode(t, "rot13") if "rot13" in t.lower() else ""
    leet = decoded.lower().translate(LEET)
    return {"normalized": decoded, "leet": leet, "rot13": rot,
            "flags": {"zero_width": text.translate(ZERO_WIDTH) != text,
                      "decoded": decoded != t, "rot13": bool(rot)}}
