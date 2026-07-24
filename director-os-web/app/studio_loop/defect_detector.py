from __future__ import annotations

from app.studio_loop.schemas import LoopDefect


def detect_defects(evaluation: dict) -> list[LoopDefect]:
    defects: list[LoopDefect] = []
    if "MASTER_AUDIO_TRUNCATED" in evaluation.get("critical_failures", []):
        defects.append(LoopDefect("MASTER_AUDIO_TRUNCATED", "critical", "Preview duration does not match master song.", "Timeline assembly duration mismatch."))
    if "BROKEN_MEDIA_URL" in evaluation.get("critical_failures", []):
        defects.append(LoopDefect("BROKEN_MEDIA_URL", "critical", "Captioned preview media is missing or not route-resolvable.", "Latest safe animatic resolver/media artifact mismatch."))
    if "MAJOR_CAPTION_OFFSET_OR_UNVERIFIED_SYNC" in evaluation.get("critical_failures", []):
        defects.append(LoopDefect("CAPTION_SYNC_UNVERIFIED", "critical", "Caption timing is not trusted for production.", "No human-approved or ASR-supported lyric alignment yet."))
    if "LIPSYNC_NOT_READY" in evaluation.get("critical_failures", []):
        defects.append(LoopDefect("LIPSYNC_PROVIDER_UNAVAILABLE", "major", "No phrase is ready for lip-sync packaging.", "Brain sync confidence and source-shot eligibility are insufficient."))
    if evaluation.get("caption_confidence", {}).get("high", 0) == 0:
        defects.append(LoopDefect("LOCAL_ASR_UNAVAILABLE", "major", "No local ASR evidence is available for Burmese singing alignment.", "No approved/detected local ASR model."))
    defects.append(LoopDefect("AI_GENERATION_UNAVAILABLE", "major", "Production AI frame count is zero.", "No approved local image/video generation backend is operational."))
    return defects
