from __future__ import annotations

from typing import Any

from app.audio.brain_sync_service import build_animatic_v15, rebuild_caption_v6
from app.audio.sync_offset_service import generate_offset_candidates


def execute_safe_repairs(repairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    did_rebuild = False
    for repair in repairs:
        if repair["action"] == "rebuild_sync_calibrated_animatic" and not did_rebuild:
            generate_offset_candidates()
            rebuild_caption_v6()
            result = build_animatic_v15()
            results.append({"repair": repair["action"], "status": "completed", "artifact": result["run_dir"]})
            did_rebuild = True
        elif repair.get("approval_required"):
            results.append({"repair": repair["action"], "status": "awaiting_approval", "summary": repair["summary"]})
        else:
            results.append({"repair": repair["action"], "status": "skipped_duplicate_or_not_applicable"})
    return results
