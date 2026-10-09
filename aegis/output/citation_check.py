"""H2: every sentence must cite an existing passage; numbers in it must appear in that passage."""
import re
from aegis.contracts import ContentItem
CITE = re.compile(r"\[(p_[0-9a-f]{8})\]")

def split_sentences(answer: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?\]])\s+(?=[A-Z])", answer) if s.strip()]

def check(answer: str, passages: dict[str, ContentItem]) -> list[dict]:
    out = []
    for s in split_sentences(answer):
        ids = CITE.findall(s)
        ok_ids = [i for i in ids if i in passages]
        nums = re.findall(r"\d[\d,.]*\d|\d", CITE.sub("", s))
        src = " ".join(passages[i].text for i in ok_ids)
        missing = [n for n in nums if n.rstrip(".") not in src]
        out.append({"sentence": s, "ids": ids, "supported": bool(ok_ids) and not missing and len(ok_ids) == len(ids),
                    "missing": missing})
    return out
