from __future__ import annotations

import json
import statistics
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import ENGINE_ROOT, REPO_ROOT
from app.services.lyric_timing_service import MASTER_AUDIO
from app.services.v104_animatic_sync_service import _make_analysis_wav, _phrases, phrase_gaps


OFFSET_PATH = ENGINE_ROOT / "state" / "SYNC_OFFSET_ANALYSIS.json"
FEEDBACK_PATH = ENGINE_ROOT / "state" / "SYNC_FEEDBACK.json"
CANDIDATES_PATH = ENGINE_ROOT / "state" / "SYNC_OFFSET_CANDIDATES.json"


def analyze_caption_offset(user_report: str = "captions_ahead") -> dict[str, Any]:
    phrases = _phrases()
    wav = _make_analysis_wav()
    energy = _energy_frames(wav)
    offsets = []
    for phrase in phrases:
        start = float(phrase["final_start_time"])
        expected = _local_onset_after(energy, start)
        if expected is None:
            expected = start + 0.75 if user_report == "captions_ahead" else start
            confidence = 0.35
            reason = "user reported captions ahead; local onset weak"
        else:
            confidence = 0.58
            reason = "local RMS rise after caption onset"
        offset = round(expected - start, 3)
        offsets.append(
            {
                "phrase_id": phrase["phrase_id"],
                "phrase_index": phrase["phrase_index"],
                "expected_vocal_onset": round(expected, 3),
                "current_caption_onset": round(start, 3),
                "offset_seconds": offset,
                "ahead_or_late": "caption_ahead" if offset > 0.12 else ("caption_late" if offset < -0.12 else "near"),
                "confidence": confidence,
                "local_correction": max(0.0, min(1.5, offset)),
                "reason": reason,
            }
        )
    positive = [item["local_correction"] for item in offsets if item["ahead_or_late"] == "caption_ahead"]
    if user_report == "captions_ahead" and positive:
        global_delay = round(float(statistics.median(positive)), 3)
    elif user_report == "captions_ahead":
        global_delay = 0.75
    else:
        global_delay = 0.0
    global_delay = max(0.0, min(1.25, global_delay))
    drift = _drift_per_minute(offsets)
    same_direction = sum(1 for item in offsets if item["ahead_or_late"] == "caption_ahead")
    confidence = 0.62 if user_report == "captions_ahead" and same_direction >= max(3, len(offsets) // 3) else 0.42
    data = {
        "version": "v1.0.6",
        "user_report": user_report,
        "global_caption_delay_seconds": global_delay,
        "drift_seconds_per_minute": drift,
        "phrase_level_offsets": offsets,
        "confidence": confidence,
        "reason": "User review reported captions ahead; local RMS/onset evidence is used as support, not as word alignment.",
        "safe_to_auto_apply": bool(user_report == "captions_ahead" and global_delay > 0 and confidence >= 0.55),
        "warnings": ["not_word_or_phoneme_alignment", "review_version_only"],
    }
    OFFSET_PATH.parent.mkdir(parents=True, exist_ok=True)
    OFFSET_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return data


def offset_status() -> dict[str, Any]:
    if OFFSET_PATH.exists():
        try:
            return json.loads(OFFSET_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return analyze_caption_offset()


def save_sync_feedback(
    action: str,
    phrase_id: int | None = None,
    seconds: float = 0.0,
    note: str = "",
    current_run: int | None = None,
    old_start: float | None = None,
    old_end: float | None = None,
    new_start: float | None = None,
    new_end: float | None = None,
    confidence_before: float | None = None,
    confidence_after: float | None = None,
    applied_by: str = "user",
) -> dict[str, Any]:
    data = sync_feedback()
    before = float(data.get("global_user_offset_seconds") or 0)
    event = {
        "current_run": current_run,
        "phrase_id": phrase_id,
        "user_action": action,
        "old_start": old_start,
        "old_end": old_end,
        "new_start": new_start,
        "new_end": new_end,
        "global_offset_before": before,
        "confidence_before": confidence_before,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reason": note,
        "applied_by": applied_by,
        "seconds": seconds,
    }
    data.setdefault("events", []).append(event)
    if action == "shift_all_later":
        data["global_user_offset_seconds"] = float(data.get("global_user_offset_seconds") or 0) + abs(seconds)
    if action == "shift_all_earlier":
        data["global_user_offset_seconds"] = float(data.get("global_user_offset_seconds") or 0) - abs(seconds)
    if action == "approve_global_offset":
        data["approved_global_offset_seconds"] = seconds
    event["global_offset_after"] = float(data.get("global_user_offset_seconds") or 0)
    event["confidence_after"] = confidence_after
    FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    FEEDBACK_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return data


def sync_feedback() -> dict[str, Any]:
    if FEEDBACK_PATH.exists():
        try:
            return json.loads(FEEDBACK_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"version": "v1.0.7", "global_user_offset_seconds": 0.0, "approved_global_offset_seconds": None, "events": []}


def corrected_time(start: float, end: float, offset: dict[str, Any]) -> tuple[float, float, float]:
    user_offset = float(sync_feedback().get("global_user_offset_seconds") or 0)
    auto_offset = float(offset.get("global_caption_delay_seconds") or 0) if offset.get("safe_to_auto_apply") else 0.0
    applied = max(-2.0, min(2.0, auto_offset + user_offset))
    return max(0.0, start + applied), max(0.05, end + applied), applied


def generate_offset_candidates() -> dict[str, Any]:
    offset = offset_status()
    feedback = sync_feedback()
    phrase_offsets = offset.get("phrase_level_offsets", [])
    local_values = [float(item.get("local_correction") or 0) for item in phrase_offsets]
    detected_median = round(float(statistics.median(local_values)), 3) if local_values else float(offset.get("global_caption_delay_seconds") or 0)
    feedback_values = _feedback_seconds(feedback)
    feedback_median = round(float(statistics.median(feedback_values)), 3) if feedback_values else None
    current = round(float(offset.get("global_caption_delay_seconds") or 0) + float(feedback.get("global_user_offset_seconds") or 0), 3)
    raw = [current, 0.6, 0.8, 1.0, 1.2, detected_median]
    if feedback_median is not None:
        raw.append(feedback_median)
    candidates = []
    for value in sorted({round(max(-1.0, min(2.0, float(item))), 3) for item in raw}):
        metrics = _candidate_metrics(value, phrase_offsets)
        candidates.append({"offset_seconds": value, **metrics})
    best = sorted(candidates, key=lambda item: item["score"])[0] if candidates else {"offset_seconds": current}
    data = {
        "version": "v1.0.7",
        "current_offset_seconds": current,
        "detected_vocal_onset_median": detected_median,
        "feedback_median": feedback_median,
        "best_candidate": best,
        "candidates": candidates,
        "approved_global_offset_seconds": feedback.get("approved_global_offset_seconds"),
        "reason": "Candidate offsets are scored against local vocal-onset evidence and phrase coverage. This is not ASR or phoneme alignment.",
        "auto_apply_allowed": bool(feedback.get("approved_global_offset_seconds") is not None),
    }
    CANDIDATES_PATH.parent.mkdir(parents=True, exist_ok=True)
    CANDIDATES_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return data


def offset_candidates_status() -> dict[str, Any]:
    if CANDIDATES_PATH.exists():
        try:
            return json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return generate_offset_candidates()


def sync_calibration_status() -> dict[str, Any]:
    candidates = generate_offset_candidates()
    feedback = sync_feedback()
    events = feedback.get("events", [])
    return {
        "version": "v1.0.7",
        "run14_offset_seconds": offset_status().get("global_caption_delay_seconds"),
        "current_offset_seconds": candidates["current_offset_seconds"],
        "proposed_offset_seconds": candidates["best_candidate"].get("offset_seconds"),
        "candidate_count": len(candidates["candidates"]),
        "approved_global_offset_seconds": feedback.get("approved_global_offset_seconds"),
        "feedback_event_count": len(events),
        "phrase_feedback_count": sum(1 for event in events if event.get("phrase_id") is not None),
        "global_feedback_count": sum(1 for event in events if event.get("phrase_id") is None),
        "suggested_next_action": "approve proposed global offset" if feedback.get("approved_global_offset_seconds") is None else "rebuild Run 15 review animatic",
        "candidates": candidates,
        "feedback": feedback,
    }


def _candidate_metrics(offset_seconds: float, phrase_offsets: list[dict[str, Any]]) -> dict[str, Any]:
    local = [float(item.get("local_correction") or item.get("offset_seconds") or 0) for item in phrase_offsets]
    if not local:
        return {
            "average_distance_to_vocal_onset": 0,
            "captions_starting_before_vocal_onset_count": 0,
            "captions_inside_silence_count": 0,
            "captions_overlapping_instrumental_gaps_count": 0,
            "phrase_coverage_score": 0,
            "likely_readability_score": 0,
            "score": 0,
            "reason": "no local phrase offset evidence",
        }
    distances = [abs(offset_seconds - item) for item in local]
    before = sum(1 for item in local if offset_seconds < item - 0.12)
    late = sum(1 for item in local if offset_seconds > item + 0.85)
    average = round(sum(distances) / len(distances), 3)
    coverage = round(max(0.0, 1.0 - (before / max(1, len(local)))), 3)
    readability = round(max(0.0, 1.0 - (late / max(1, len(local)))), 3)
    score = round((before * 1.5) + (late * 0.9) + average, 3)
    return {
        "average_distance_to_vocal_onset": average,
        "captions_starting_before_vocal_onset_count": before,
        "captions_inside_silence_count": before,
        "captions_overlapping_instrumental_gaps_count": 0,
        "phrase_coverage_score": coverage,
        "likely_readability_score": readability,
        "score": score,
        "reason": "fewer captions start before detected vocal onset" if before else "caption starts are not before detected vocal onsets",
    }


def _feedback_seconds(feedback: dict[str, Any]) -> list[float]:
    values = []
    base = float(offset_status().get("global_caption_delay_seconds") or 0)
    for event in feedback.get("events", []):
        action = event.get("user_action") or event.get("action")
        seconds = float(event.get("seconds") or 0)
        if action in {"shift_all_later", "caption_too_early", "too_early"}:
            values.append(base + abs(seconds))
        if action in {"shift_all_earlier", "caption_too_late", "too_late"}:
            values.append(base - abs(seconds))
    approved = feedback.get("approved_global_offset_seconds")
    if approved is not None:
        values.append(float(approved))
    return values


def _energy_frames(wav: Path) -> list[dict[str, float]]:
    frames = []
    with wave.open(str(wav), "rb") as handle:
        rate = handle.getframerate()
        chunk = max(1, int(rate * 0.05))
        index = 0
        while True:
            raw = handle.readframes(chunk)
            if not raw:
                break
            samples = [int.from_bytes(raw[i : i + 2], "little", signed=True) for i in range(0, len(raw) - 1, 2)]
            if samples:
                rms = (sum(sample * sample for sample in samples) / len(samples)) ** 0.5 / 32768.0
                frames.append({"time": index * 0.05, "rms": rms})
            index += 1
    return frames


def _local_onset_after(energy: list[dict[str, float]], caption_start: float) -> float | None:
    window = [item for item in energy if caption_start - 0.4 <= item["time"] <= caption_start + 1.8]
    if len(window) < 5:
        return None
    baseline = statistics.median([item["rms"] for item in window[: max(3, min(8, len(window) // 3))]])
    threshold = max(baseline * 1.45, baseline + 0.025)
    for item in window:
        if item["time"] >= caption_start and item["rms"] >= threshold:
            return float(item["time"])
    return None


def _drift_per_minute(offsets: list[dict[str, Any]]) -> float:
    if len(offsets) < 2:
        return 0.0
    first = offsets[0]
    last = offsets[-1]
    minutes = max((float(last["current_caption_onset"]) - float(first["current_caption_onset"])) / 60.0, 0.001)
    return round((float(last["offset_seconds"]) - float(first["offset_seconds"])) / minutes, 4)
