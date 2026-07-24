from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import REPO_ROOT
from app.services.autonomous_director_service import collect_project_evidence, director_status


def build_stage_context(project_path: str | Path, idea: str, stage: str) -> dict[str, Any]:
    project = Path(project_path).expanduser().resolve()
    evidence = collect_project_evidence(project)
    status = director_status()
    return {
        "project_path": str(project),
        "idea": idea,
        "stage": stage,
        "existing_state": status.get("state", {}),
        "evidence_summary": {
            "file_counts": evidence.get("file_counts", {}),
            "selected_clip_count": len(evidence.get("selected_clips", [])),
            "rejected_clip_count": len(evidence.get("rejected_clips", [])),
            "contact_sheet_count": len(evidence.get("contact_sheets", [])),
            "documents": list(evidence.get("documents", {}).keys()),
        },
        "locked_truth": {
            "project": "Burmese heartbreak music video",
            "performer": "consenting adult wife performer",
            "location": "approved dark teak Finnish bar/stage",
            "hard_negatives": ["karaoke", "kung fu", "martial arts", "K-pop", "TikTok", "fake lip-sync", "fake body proportions"],
        },
    }


def stage_prompt(context: dict[str, Any]) -> str:
    return (
        "You are Director OS, an autonomous professional film director engine. "
        "Return ONLY a valid JSON object with keys: stage, summary, confidence, sources, artifacts, blockers, data. "
        "Do not include markdown. Do not request cloud upload, paid APIs, model downloads, publishing, or deletion. "
        "Use the project evidence and preserve approved/rejected decisions.\n\n"
        f"CONTEXT_JSON:\n{json.dumps(context, ensure_ascii=False, indent=2)}"
    )


def default_project_path() -> Path:
    return REPO_ROOT
