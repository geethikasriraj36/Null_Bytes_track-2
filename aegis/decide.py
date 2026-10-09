
import re
from typing import Any


POLICY_VERSION = "0.1.0"

# Prototype rules. These are heuristics, not a production security boundary.
BLOCK_RULES = [

    (
        "H5-001",
        r"^\s*(ignore|disregard|forget|override)\s+(all\s+)?(previous|prior|earlier)\s+instructions\b",
        "Direct instruction override attempt detected",
    ),
    (
        "H5-002",
        r"\bbypass (all )?(safety|security) rules\b",
        "Safety or security bypass requested",
    ),
    (
        "H5-003",
        r"\breveal (your )?(hidden )?(system instructions|secrets|api keys|credentials)\b",
        "Protected instructions or secrets requested",
    ),
    (
        "H5-004",
        r"\bdisclose secrets\b",
        "Secret disclosure requested",
    ),
    (
        "H5-005",
        r"\b(reveal|disclose|expose|provide|print|show)\b.{0,60}\b(private )?(api keys|credentials|passwords|secrets)\b",
        "Credential or secret disclosure requested",
    ),
    (
        "H5-006",
        r"\bwhat\b.{0,60}\b(private )?credentials\b.{0,60}\b(stored|available|environment|system)\b",
        "Indirect credential disclosure requested",
    ),
    (
        "H5-007",
        r"\b(private )?credentials\b.{0,60}\b(stored|available|environment|system)\b",
        "Credential disclosure requested",
    ),
    (
        "H5-009",
        r"\bdelete all files\b",
        "Destructive file operation requested",
    ),
    (
        "H5-010",
        r"\bsteal credentials\b",
        "Credential theft requested",
    ),
    (
        "H5-011",
        r"\b(wipe|erase|format)\b.{0,80}\b(disk|drive|backup|backups|files)\b",
        "Destructive disk or backup operation requested",
    ),
    (
        "H5-012",
        r"\b(disk|drive|backup|backups|files)\b.{0,80}\b(wipe|erase|format)\b",
        "Destructive disk or backup operation requested",
    ),

(
    "H5-013",
    r"\b(disregard|forget|override)\b.{0,60}\b(all|every|any|previous|prior|earlier)?\s*\b(instruction|instructions|rule|rules)\b",
    "Instruction override attempt detected",
),

    (
        "H5-014",
        r"\b(no|without|remove)\b.{0,30}\b(safety restrictions|safety limits|safeguards)\b.{0,80}\b(reveal|expose|disclose|show|print)\b",
        "Safety bypass and protected disclosure requested",
    ),
]


def decide_with_reason(prompt: str, config: str = "7_full") -> dict[str, Any]:
    """Return a decision and its explanation for evaluation and auditing."""
    if not isinstance(prompt, str):
        raise TypeError("prompt must be a string")

    if config == "0_baseline":
        return {
            "decision": "allow",
            "rule_id": "BASELINE-ALLOW",
            "reason": "Baseline configuration allows every request",
            "policy_version": POLICY_VERSION,
        }

    if config != "7_full":
        raise ValueError(f"Unknown configuration: {config}")

    for rule_id, pattern, reason in BLOCK_RULES:
        if re.search(pattern, prompt, flags=re.IGNORECASE):
            return {
                "decision": "block",
                "rule_id": rule_id,
                "reason": reason,
                "policy_version": POLICY_VERSION,
            }

    return {
        "decision": "allow",
        "rule_id": "DEFAULT-ALLOW",
        "reason": "No configured blocking rule matched",
        "policy_version": POLICY_VERSION,
    }


def decide(prompt: str, config: str = "7_full") -> str:
    """Simple interface for components that only need allow/block."""
    return decide_with_reason(prompt, config)["decision"]
