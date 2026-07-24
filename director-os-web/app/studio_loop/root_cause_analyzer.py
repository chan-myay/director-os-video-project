from __future__ import annotations


def analyze_root_causes(defects: list[dict]) -> list[dict]:
    rows = []
    for defect in defects:
        rows.append(
            {
                "defect_code": defect["code"],
                "root_cause": defect["root_cause"],
                "lowest_cost_safe_repair": _repair_for(defect["code"]),
                "approval_need": defect["code"] in {"LOCAL_ASR_UNAVAILABLE", "AI_GENERATION_UNAVAILABLE", "LIPSYNC_PROVIDER_UNAVAILABLE"},
            }
        )
    return rows


def _repair_for(code: str) -> str:
    return {
        "MASTER_AUDIO_TRUNCATED": "rebuild full-song animatic with master audio duration as authority",
        "BROKEN_MEDIA_URL": "refresh latest-safe animatic resolver and media references",
        "CAPTION_SYNC_UNVERIFIED": "generate sync-calibrated candidates and rebuild review captions",
        "LOCAL_ASR_UNAVAILABLE": "request one local ASR setup approval or continue with listening review",
        "AI_GENERATION_UNAVAILABLE": "request one local storyboard model approval or continue with composite previs",
        "LIPSYNC_PROVIDER_UNAVAILABLE": "wait for brain-sync approval and provider setup",
    }.get(code, "manual review")
