from __future__ import annotations

from app.studio_loop.schemas import LoopRepair


def plan_repairs(defects: list[dict]) -> list[LoopRepair]:
    repairs: list[LoopRepair] = []
    for defect in defects:
        code = defect["code"]
        if code in {"MASTER_AUDIO_TRUNCATED", "BROKEN_MEDIA_URL", "CAPTION_SYNC_UNVERIFIED"}:
            repairs.append(LoopRepair(code, "rebuild_sync_calibrated_animatic", "planned", False, "Rebuild v15 full-song sync-calibrated review from brain timeline."))
        elif code == "LOCAL_ASR_UNAVAILABLE":
            repairs.append(LoopRepair(code, "request_local_asr_setup", "requires_approval", True, "Consolidated local ASR setup approval required for stronger lyric alignment."))
        elif code == "AI_GENERATION_UNAVAILABLE":
            repairs.append(LoopRepair(code, "request_local_storyboard_model", "requires_approval", True, "Consolidated local storyboard/image model approval required for real AI frames."))
        elif code == "LIPSYNC_PROVIDER_UNAVAILABLE":
            repairs.append(LoopRepair(code, "wait_for_lipsync_prerequisites", "blocked", True, "Lip-sync requires approved sync and provider setup."))
    return repairs
