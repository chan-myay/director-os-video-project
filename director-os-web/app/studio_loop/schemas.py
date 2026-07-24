from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


STAGES = [
    "understand",
    "research",
    "direct",
    "generate",
    "assemble",
    "watch_listen",
    "find_problems",
    "fix",
    "review",
]


@dataclass
class LoopDefect:
    code: str
    severity: str
    symptom: str
    root_cause: str
    affected_artifact: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LoopRepair:
    defect_code: str
    action: str
    status: str
    approval_required: bool = False
    summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AcceptanceResult:
    status: str
    score: float
    critical_failures: list[str]
    approvals_required: list[dict[str, Any]]
    next_action: str
