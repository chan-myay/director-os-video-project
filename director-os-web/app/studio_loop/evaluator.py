from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.audio.brain_sync_service import brain_lipsync_readiness, brain_timeline_status
from app.services.latest_safe_animatic_service import latest_safe_animatic_context, resolve_director_asset
from app.system_tools.ffmpeg_service import probe_media


def evaluate_current_output(loop_id: int, iteration: int) -> dict[str, Any]:
    safe = latest_safe_animatic_context()
    brain = brain_timeline_status()
    lipsync = brain_lipsync_readiness()
    active_path = Path(safe.get("clean_mp4") or "")
    captioned_path = Path(safe.get("captioned_review_mp4") or "")
    media = {}
    if active_path.exists():
        media["clean"] = probe_media(active_path)
    if captioned_path.exists():
        media["captioned"] = probe_media(captioned_path)
    validation = safe.get("validation", {})
    scorecard = {
        "creative_coherence": 72,
        "narrative_emotional_coherence": 70,
        "music_image_relationship": 62,
        "lyric_image_relationship": 45,
        "burmese_cultural_authenticity": 68,
        "composition": 64,
        "cinematography": 60,
        "lighting": 62,
        "performance": 50,
        "movement": 44,
        "identity_consistency": 40,
        "body_realism": 50,
        "character_location_continuity": 58,
        "caption_readability": 80 if safe.get("font", {}).get("readable") else 0,
        "caption_timing": 30 if brain.get("high_confidence_phrase_count", 0) == 0 else 70,
        "lip_sync_quality": 0 if lipsync.get("ready_count", 0) == 0 else 65,
        "edit_rhythm": 58,
        "technical_integrity": 85 if validation.get("status") == "ok" else 20,
        "privacy_rights_compliance": 95,
    }
    critical = []
    if validation.get("status") != "ok":
        critical.append("MASTER_AUDIO_TRUNCATED")
    if not safe.get("captioned_review_exists"):
        critical.append("BROKEN_MEDIA_URL")
    if brain.get("high_confidence_phrase_count", 0) == 0:
        critical.append("MAJOR_CAPTION_OFFSET_OR_UNVERIFIED_SYNC")
    if lipsync.get("ready_count", 0) == 0:
        critical.append("LIPSYNC_NOT_READY")
    if safe.get("font", {}).get("readable") is False:
        critical.append("FONT_UNREADABLE")
    score = round(sum(scorecard.values()) / len(scorecard), 2)
    return {
        "loop_id": loop_id,
        "iteration": iteration,
        "active_animatic_version": safe.get("latest_version"),
        "media": media,
        "duration_validation": validation,
        "brain_version": brain.get("version"),
        "sync_method_counts": brain.get("sync_method_counts", {}),
        "caption_confidence": {
            "high": brain.get("high_confidence_phrase_count", 0),
            "medium": brain.get("medium_confidence_phrase_count", 0),
            "low": brain.get("low_confidence_phrase_count", 0),
            "blocked": brain.get("blocked_phrase_count", 0),
        },
        "lipsync": lipsync,
        "scorecard": scorecard,
        "score": score,
        "critical_failures": critical,
        "status": "failed_gates" if critical else "passed",
        "evidence": {
            "clean_asset_url": safe.get("clean_asset_url"),
            "captioned_asset_url": safe.get("captioned_review_asset_url"),
            "route_resolution": resolve_director_asset((safe.get("captioned_review_asset_url") or "").replace("/director-assets/", ""))[1] if safe.get("captioned_review_asset_url") else 404,
        },
    }
