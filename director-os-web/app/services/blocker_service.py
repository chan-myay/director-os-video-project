from __future__ import annotations

from typing import Any


BLOCKER_DEFINITIONS: dict[str, dict[str, Any]] = {
    "LOCAL_STORYBOARD_MODEL_REQUIRED": {
        "severity": "approval_required",
        "blocks": ["ai_storyboard_generation"],
        "does_not_block": ["director treatment", "storyboard structure", "composite previs", "captions", "animatic", "production planning"],
    },
    "VOICE_PROVIDER_NOT_CONFIGURED": {
        "severity": "optional_capability",
        "blocks": ["generated voice samples"],
        "does_not_block": ["caption planning", "director plan", "storyboard", "animatic", "renderer planning"],
    },
    "FFMPEG_REQUIRED_FOR_MP4_ANIMATIC": {
        "severity": "hard_blocker",
        "blocks": ["mp4_animatic"],
        "does_not_block": ["director treatment", "storyboard", "caption planning"],
    },
    "CODEX_PROVIDER_USAGE_LIMIT": {
        "severity": "warning",
        "blocks": ["real Codex full acceptance run until quota resets or credits are added"],
        "does_not_block": ["director treatment", "storyboard structure", "composite previs", "captions", "mp4 animatic", "production planning"],
    },
}


def classify_blockers(blockers: list[str]) -> list[dict[str, Any]]:
    classified = []
    for blocker in blockers:
        if blocker.startswith("PROVIDER_FALLBACK_USED:"):
            definition = {
                "severity": "warning",
                "blocks": [],
                "does_not_block": ["director package when local fallback artifacts are present"],
            }
        else:
            definition = BLOCKER_DEFINITIONS.get(
                blocker,
                {"severity": "warning", "blocks": [], "does_not_block": []},
            )
        classified.append({"code": blocker, **definition})
    return classified


def grouped_blockers(blockers: list[str]) -> dict[str, list[dict[str, Any]]]:
    groups = {
        "hard_blockers": [],
        "required_inputs": [],
        "approvals_needed": [],
        "optional_capabilities": [],
        "warnings": [],
        "informational": [],
    }
    for item in classify_blockers(blockers):
        severity = item["severity"]
        if severity == "hard_blocker":
            groups["hard_blockers"].append(item)
        elif severity == "required_input":
            groups["required_inputs"].append(item)
        elif severity == "approval_required":
            groups["approvals_needed"].append(item)
        elif severity == "optional_capability":
            groups["optional_capabilities"].append(item)
        elif severity == "informational":
            groups["informational"].append(item)
        else:
            groups["warnings"].append(item)
    return groups


def readiness_from_blockers(blockers: list[str]) -> str:
    groups = grouped_blockers(blockers)
    if groups["hard_blockers"]:
        return "awaiting_required_input"
    if groups["approvals_needed"]:
        return "ready_with_approvals"
    return "ready"
