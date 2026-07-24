from __future__ import annotations

from typing import Any

from app.audio.sync_confidence_service import confidence_for_boundary


def match_phrases_to_boundaries(phrases: list[dict[str, Any]], instrumental_gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matches = []
    for row in phrases:
        start = float(row["final_start_time"])
        end = float(row["final_end_time"])
        before = max((float(gap["duration"]) for gap in instrumental_gaps if abs(float(gap["end"]) - start) <= 0.08), default=0.0)
        after = max((float(gap["duration"]) for gap in instrumental_gaps if abs(float(gap["start"]) - end) <= 0.08), default=0.0)
        confidence, reason, needs_review = confidence_for_boundary(end - start, before, after)
        display = row.get("approved_display_text") or row.get("normalized_unicode") or row.get("original_text") or ""
        matches.append(
            {
                "phrase_id": row["phrase_id"],
                "phrase_index": row["phrase_index"],
                "lyric_line": display,
                "source_original": row.get("original_text", ""),
                "candidate_start": start,
                "candidate_end": end,
                "duration": end - start,
                "timing_method": "level_b_existing_vocal_boundary_plus_phrase_order",
                "timing_status": row.get("listening_sync_status") or "auto_boundary_unverified",
                "confidence": round(confidence, 3),
                "reason": reason,
                "needs_human_review": needs_review or row.get("listening_sync_status") != "correct_line_verified",
                "likely_wrong_line": row.get("listening_sync_status") == "wrong_line",
                "instrumental_gap_before": round(before, 3),
                "instrumental_gap_after": round(after, 3),
                "overlap_status": "ok",
                "caption_safe": bool(display and not row.get("listening_sync_status") == "wrong_line"),
                "song_timebase": "master_audio_seconds",
                "review_label": "AUTO_BOUNDARY_UNVERIFIED" if row.get("listening_sync_status") != "correct_line_verified" else "HUMAN_LISTENING_VERIFIED",
            }
        )
    return matches
