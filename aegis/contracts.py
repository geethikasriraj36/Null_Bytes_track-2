"""Shared data contracts. Frozen at hour 2. Changes need M1's approval."""
from __future__ import annotations
from typing import Literal, Any
from pydantic import BaseModel, Field
import uuid, time

Source = Literal["user", "doc", "tool", "web", "memory"]
Label = Literal["public", "internal", "secret"]
Decision = Literal["pass", "flag", "strict", "refuse", "quarantine", "review",
                   "redact", "block", "confirm", "allow", "abstain", "prune"]

class Verdict(BaseModel):
    layer: str                      # e.g. "J1", "A2", "QGATE", "T2"
    decision: Decision
    score: float = 0.0              # 0 = safe, 1 = certainly bad
    reason: str = ""                # internal reason code, never shown to user
    details: dict[str, Any] = Field(default_factory=dict)

class ContentItem(BaseModel):
    id: str = Field(default_factory=lambda: "p_" + uuid.uuid4().hex[:8])
    text: str
    source: Source
    origin: str = ""                # tool name, file path, URL
    label: Label = "internal"
    tainted: bool = True            # everything except the user's own message
    redactions: int = 0

class ToolCall(BaseModel):
    call_id: str = Field(default_factory=lambda: "c_" + uuid.uuid4().hex[:8])
    name: str
    args: dict[str, Any]
    tainted_args: list[str] = Field(default_factory=list)  # arg names whose value came from tainted content

class GateDecision(BaseModel):
    decision: Literal["ALLOW", "CONFIRM", "BLOCK"]
    verdicts: list[Verdict]
    token: str | None = None        # HMAC token, only when ALLOW (or CONFIRM after approval)

class SessionState(BaseModel):
    session_id: str
    user_id: str = "demo_user"
    permissions: list[Label] = ["public", "internal"]
    risk: float = 0.0               # J3 multi-turn risk
    strict: bool = False
    seen_tainted: bool = False      # any untrusted content in this session
    seen_private: bool = False      # any internal/secret data in this session (T7)
    tool_calls: dict[str, int] = Field(default_factory=dict)  # T6 counters
    qgate_review: bool = False      # Q-Gate flagged something this session -> escalate tier 2+
    turn: int = 0
    retrieved: bool = False         # this turn read docs/files/db -> H checks apply
    pinned: list[str] = Field(default_factory=list)          # A1: tools allowed for this task
    passages: dict[str, ContentItem] = Field(default_factory=dict)  # vetted passages by id (H1/H2)
    messages: list[dict] = Field(default_factory=list)        # LLM message history (OpenAI format)
    pending: ToolCall | None = None                           # call waiting for human confirmation (T4)

class TurnResult(BaseModel):
    answer: str
    verdicts: list[Verdict]
    pending_confirmation: ToolCall | None = None
    refused: bool = False
    trace: dict[str, Any] = Field(default_factory=dict)   # optional, additive: UI "stats for nerds" (aegis/trace.py)
