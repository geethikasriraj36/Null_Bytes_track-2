"""J1 step 1: undo common obfuscation before classifying."""
import base64, binascii, codecs, re, unicodedata

ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff\u00ad\u180e\u2061\u2062\u2063\u2064"), None)
# NFKC does not fold cross-script look-alikes (Cyrillic/Greek letters that look Latin)
HOMOGLYPHS = str.maketrans("аеорсухіјѕԁɡΑΒΕΗΙΚΜΝΟΡΤΧΥΖ", "aeopcyxijsdgABEHIKMNOPTXYZ")
LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})
B64 = re.compile(r"(?<![\w+/])[A-Za-z0-9+/_-]{16,}={0,2}")
HEX = re.compile(r"\b(?:[0-9a-fA-F]{2}){8,}\b")

def _readable(s: str) -> bool:
    return bool(s) and all(c.isprintable() or c in "\n\t\r" for c in s) and sum(c.isalpha() or c == " " for c in s) >= 0.7 * len(s)

def _try_b64(m):
    tok = m.group(0)
    if tok.isalpha():                 # a plain long word ("internationalization"), not an encoding
        return tok
    for dec in (base64.b64decode, base64.urlsafe_b64decode):
        try:
            out = dec(tok + "=" * (-len(tok) % 4)).decode("utf-8")
            if _readable(out):
                return out
        except (binascii.Error, UnicodeDecodeError, ValueError):
            pass
    return tok

def _try_hex(m):
    try:
        out = bytes.fromhex(m.group(0)).decode("utf-8")
        return out if _readable(out) else m.group(0)
    except (ValueError, UnicodeDecodeError):
        return m.group(0)

def normalize(text: str) -> dict:
    """Returns the views the classifier should see, plus flags for the audit log."""
    t = text.translate(ZERO_WIDTH)
    t = unicodedata.normalize("NFKC", t)          # folds full-width and many compatibility forms
    folded = t.translate(HOMOGLYPHS)
    decoded = HEX.sub(_try_hex, B64.sub(_try_b64, folded))
    rot = codecs.decode(folded, "rot13") if "rot13" in folded.lower().replace("-", "").replace(" ", "") else ""
    leet = decoded.lower().translate(LEET)
    return {"normalized": decoded, "leet": leet, "rot13": rot,
            "flags": {"zero_width": text.translate(ZERO_WIDTH) != text,
                      "homoglyph": folded != t,
                      "decoded": decoded != folded, "rot13": bool(rot)}}
