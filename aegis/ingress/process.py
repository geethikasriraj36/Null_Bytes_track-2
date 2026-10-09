
from dataclasses import dataclass, field
from typing import Any

from aegis.ingress.scan import canary_hit, redact, scan


@dataclass
class ContentItem:
    text: str
    source: str
    label: str = "internal"
    allowed_roles: list[str] = field(default_factory=lambda: ["user", "agent", "admin"])
    tainted: bool = True
    canary_hits: list[str] = field(default_factory=list)
    scan_matches: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    accessible: bool = True


LABEL_ACCESS = {
    "public": {"user", "agent", "admin"},
    "internal": {"agent", "admin"},
    "confidential": {"admin"},
    "restricted": set(),
}


def process(
    text: str,
    *,
    source: str,
    label: str = "internal",
    user_role: str = "agent",
    allowed_roles: list[str] | None = None,
    redact_sensitive: bool = True,
    metadata: dict[str, Any] | None = None,
) -> ContentItem:
    """
    Apply ACL checks, scan for canaries and sensitive values,
    redact sensitive values, and attach provenance/taint metadata.

    Access is denied before content is returned if the role is not allowed.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    if not source or not isinstance(source, str):
        raise ValueError("source must be a non-empty string")

    if label not in LABEL_ACCESS:
        raise ValueError(f"Unknown sensitivity label: {label}")

    roles = set(allowed_roles) if allowed_roles is not None else LABEL_ACCESS[label]
    if user_role not in roles:
        return ContentItem(
            text="[ACCESS DENIED]",
            source=source,
            label=label,
            allowed_roles=sorted(roles),
            tainted=True,
            metadata={
                **(metadata or {}),
                "access_denied": True,
                "original_source": source,
            },
            accessible=False,
        )

    hits = canary_hit(text)
    scan_result = scan(text)
    cleaned = redact(text) if redact_sensitive else text

    return ContentItem(
        text=cleaned,
        source=source,
        label=label,
        allowed_roles=sorted(roles),
        tainted=True,
        canary_hits=hits,
        scan_matches=scan_result["matches"],
        metadata={
            **(metadata or {}),
            "source": source,
            "label": label,
            "tainted": True,
            "redacted": redact_sensitive and cleaned != text,
            "access_denied": False,
        },
        accessible=True,
    )