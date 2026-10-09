"""Ingress: D1 ACL + label, D3 canary check, D2 redaction, provenance + taint tag."""
from aegis.contracts import ContentItem, SessionState, Verdict
from aegis.ingress.scan import scan, canary_hit

def label_for(origin: str) -> str:
    if "secret" in origin: return "secret"
    if origin.startswith("public") or origin.endswith("faq.md"): return "public"
    return "internal"

def process(raw: str, source: str, origin: str, state: SessionState, enabled: bool = True) -> tuple[ContentItem, list[Verdict]]:
    item = ContentItem(text=raw, source=source, origin=origin, label=label_for(origin), tainted=source != "user")
    if not enabled:
        return item, []
    v = []
    if item.label not in state.permissions:                         # D1
        item.text = "[ACCESS DENIED]"
        v.append(Verdict(layer="D1", decision="block", score=1, reason="acl"))
    if canary_hit(item.text):                                       # D3 (before redaction)
        v.append(Verdict(layer="D3", decision="flag", score=1, reason="canary_in_ingress"))
    item.text, found = scan(item.text)                              # D2
    item.redactions = len(found)
    if found:
        v.append(Verdict(layer="D2", decision="redact", score=0.5, details={"types": found}))
    if item.tainted: state.seen_tainted = True
    if item.label in ("internal", "secret"): state.seen_private = True
    return item, v
