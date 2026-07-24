from __future__ import annotations

from typing import Any

from app.services.director_workspace_service import list_storyboard_cards
from app.services.lyric_timing_service import build_lyric_timing_authority, phrase_for_shot_time


def classify_lipsync_shots() -> list[dict[str, Any]]:
    build_lyric_timing_authority()
    cards = list_storyboard_cards()
    results = []
    for card in cards:
        shot_number = card["shot_number"]
        section = (card.get("song_section") or "").lower()
        framing = (card.get("framing") or "").lower()
        movement = " ".join([card.get("exact_movement", ""), card.get("camera_movement", ""), card.get("body_motion_risk", "")]).lower()
        start_seconds = tc_seconds(card.get("timecode_start", ""))
        end_seconds = tc_seconds(card.get("timecode_end", "")) or start_seconds + 4
        phrase = phrase_for_shot_time(start_seconds, end_seconds)
        lyric = phrase.get("caption_text", "") if phrase else ""
        state = "lipsync_optional"
        reasons = []
        if "instrumental" in section or not lyric:
            state = "instrumental_or_nonvocal"
            reasons.append("No confident vocal lyric attached.")
        if any(word in framing for word in ["wide", "silhouette"]) or "face small" in card.get("performer_action", "").lower():
            state = "face_too_small"
            reasons.append("Face is too small/profile/silhouette for reliable mouth review.")
        if any(word in movement for word in ["dance", "side", "travel", "high"]):
            if state == "lipsync_optional":
                state = "motion_too_complex"
            reasons.append("Movement-heavy coverage should not receive automatic lip-sync.")
        if "close" in framing or "medium" in framing:
            if state in {"lipsync_optional"}:
                state = "lipsync_required" if lyric else "lipsync_optional"
                reasons.append("Readable face and vocal phrase may benefit from lip-sync.")
        if shot_number in {"F01", "F02", "F03"}:
            reasons.append("Known missing coverage is face-safe movement, not singing/lip-sync.")
        results.append(
            {
                "shot_id": shot_number,
                "song_timecode": card.get("timecode_start", ""),
                "lyric_line": lyric,
                "phrase_id": phrase.get("phrase_id") if phrase else 0,
                "phrase_index": phrase.get("phrase_index") if phrase else 0,
                "phrase_start": phrase.get("final_start_time") if phrase else 0,
                "phrase_end": phrase.get("final_end_time") if phrase else 0,
                "timing_source": phrase.get("final_timing_source") if phrase else "",
                "source_clip": card.get("source_or_missing_shot_id", ""),
                "face_visibility": "small_or_profile" if state in {"face_too_small", "motion_too_complex"} else "medium_unknown",
                "motion_risk": card.get("body_motion_risk", "UNKNOWN"),
                "identity_risk": card.get("identity_risk", "UNKNOWN"),
                "eligibility": state,
                "recommended_method": recommended_method(state),
                "expected_benefit": expected_benefit(state),
                "expected_failure_modes": failure_modes(state),
                "reasons": reasons,
            }
        )
    return results


def tc_seconds(value: str) -> float:
    try:
        minutes, seconds = value.split(":")
        return int(minutes) * 60 + float(seconds)
    except Exception:
        return 0.0


def recommended_method(state: str) -> str:
    if state == "lipsync_required":
        return "infinitetalk_video_to_video_after_edit_lock"
    if state == "lipsync_optional":
        return "manual_review_then_infinitetalk_if_face_readable"
    return "do_not_lipsync"


def expected_benefit(state: str) -> str:
    if state in {"lipsync_required", "lipsync_optional"}:
        return "Can align visible mouth motion to approved song audio after edit lock."
    return "Avoids damaging face/body continuity on shots where mouth sync is not needed."


def failure_modes(state: str) -> list[str]:
    common = ["identity drift", "mouth deformation", "temporal flicker", "audio offset"]
    if state in {"face_too_small", "motion_too_complex", "lipsync_unsafe"}:
        return common + ["unreviewable small mouth", "body deformation", "background instability"]
    return common
