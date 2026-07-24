from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.audio.auto_sync_service import (
    ANIMATIC_ROOT,
    CAPTION_V4_ROOT,
    FONT_PREVIEW_ROOT,
    _render_srt,
    _render_vtt,
    font_render_preview,
)
from app.audio.auto_sync_service import auto_sync_lyrics as build_auto_sync
from app.audio.sync_offset_service import analyze_caption_offset, corrected_time, offset_status, save_sync_feedback, sync_feedback
from app.audio.sync_offset_service import generate_offset_candidates, offset_candidates_status, sync_calibration_status
from app.config import ENGINE_ROOT
from app.services.director_workspace_service import list_storyboard_cards
from app.services.lyric_timing_service import MASTER_AUDIO, voice_sync_summary
from app.services.v104_animatic_sync_service import (
    _ass,
    _escape_filter_path,
    _probe_optional,
    _run_ffmpeg,
    duration_validation,
    frame_entries_for_full_song,
    music_analysis,
)
from app.system_tools.ffmpeg_service import ffmpeg_path, probe_media


BRAIN_TIMELINE_PATH = ENGINE_ROOT / "state" / "PRODUCTION_BRAIN_TIMELINE.json"
LYRIC_EMOTION_PATH = ENGINE_ROOT / "state" / "LYRIC_MEANING_EMOTION_MAP.json"
CAPTION_V5_ROOT = ENGINE_ROOT / "captions" / "final-timing-v5"
CAPTION_V6_ROOT = ENGINE_ROOT / "captions" / "final-timing-v6"
ASR_ALIGNMENT_PATH = ENGINE_ROOT / "state" / "LOCAL_ASR_ALIGNMENT.json"


def build_brain_timeline() -> dict[str, Any]:
    analysis = music_analysis()
    auto_sync = build_auto_sync()
    offset = analyze_caption_offset("captions_ahead")
    emotion = build_lyric_meaning_emotion_map(auto_sync, analysis)
    cards = list_storyboard_cards()
    events = []
    for item in auto_sync["phrases"]:
        start, end, applied = corrected_time(float(item["candidate_start"]), float(item["candidate_end"]), offset)
        confidence = min(0.69, float(item["confidence"]) + (0.08 if offset.get("safe_to_auto_apply") else 0))
        method = "boundary_plus_global_offset" if applied else "boundary_order_estimated"
        if item.get("timing_status") == "correct_line_verified":
            method = "human_verified"
            confidence = 0.95
        matching_card = _card_for_time(cards, start, end)
        meaning = next((row for row in emotion["phrases"] if row["phrase_id"] == item["phrase_id"]), {})
        events.append(
            {
                "phrase_id": item["phrase_id"],
                "phrase_index": item["phrase_index"],
                "original_burmese": item.get("source_original", ""),
                "approved_unicode": item.get("lyric_line", ""),
                "pronunciation_helper": item.get("lyric_line", ""),
                "rough_english_meaning": meaning.get("rough_english_meaning", ""),
                "emotional_meaning": meaning.get("emotional_meaning", ""),
                "song_section": _section_for_time(start, analysis),
                "sync_method": method,
                "confidence": round(confidence, 3),
                "phrase_start": round(float(item["candidate_start"]), 3),
                "phrase_end": round(float(item["candidate_end"]), 3),
                "caption_start": round(start, 3),
                "caption_end": round(end, 3),
                "offset_applied": round(applied, 3),
                "warning": "UNVERIFIED" if confidence < 0.75 else "",
                "needs_review": confidence < 0.75,
                "shot_id": matching_card.get("shot_number", ""),
                "storyboard_relationship": matching_card.get("title", ""),
                "lip_sync_segment_start": round(start, 3),
                "lip_sync_segment_end": round(end, 3),
                "voice_segment_status": "not_tested_no_voice_audio",
                "blockers": _phrase_blockers(item, confidence),
                "user_corrections": [],
                "evidence": ["local_vocal_boundaries", "phrase_order", "rms_onset_offset", "user_report_captions_ahead"],
            }
        )
    method_counts: dict[str, int] = {}
    for event in events:
        method_counts[event["sync_method"]] = method_counts.get(event["sync_method"], 0) + 1
    data = {
        "version": "v1.0.6",
        "master_song": str(MASTER_AUDIO),
        "master_duration": probe_media(MASTER_AUDIO)["duration"],
        "song_sections": _song_sections(analysis),
        "music_analysis_path": str(ENGINE_ROOT / "state" / "MUSIC_ANALYSIS.json"),
        "offset_analysis_path": str(ENGINE_ROOT / "state" / "SYNC_OFFSET_ANALYSIS.json"),
        "lyric_meaning_emotion_path": str(LYRIC_EMOTION_PATH),
        "sync_method_counts": method_counts,
        "high_confidence_phrase_count": sum(1 for event in events if event["confidence"] >= 0.75),
        "low_confidence_phrase_count": sum(1 for event in events if event["confidence"] < 0.75),
        "blocked_phrase_count": sum(1 for event in events if event["blockers"]),
        "offset": offset,
        "feedback": sync_feedback(),
        "events": events,
        "warning": "Brain sync is corrected boundary sync, not word/phoneme alignment. Human listening review is still required.",
    }
    BRAIN_TIMELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BRAIN_TIMELINE_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return data


def brain_timeline_status() -> dict[str, Any]:
    if BRAIN_TIMELINE_PATH.exists():
        try:
            return json.loads(BRAIN_TIMELINE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return build_brain_timeline()


def build_calibrated_brain_timeline() -> dict[str, Any]:
    base = build_brain_timeline()
    candidates = generate_offset_candidates()
    feedback = sync_feedback()
    approved = feedback.get("approved_global_offset_seconds")
    selected_offset = float(approved if approved is not None else candidates["best_candidate"].get("offset_seconds", base["offset"].get("global_caption_delay_seconds", 0)))
    asr = local_asr_alignment_status()
    events = []
    for event in base["events"]:
        original_start = float(event["phrase_start"])
        original_end = float(event["phrase_end"])
        candidate_start = round(max(0.0, original_start + selected_offset), 3)
        candidate_end = round(max(0.05, original_end + selected_offset), 3)
        phrase_feedback = [item for item in feedback.get("events", []) if item.get("phrase_id") == event["phrase_id"]]
        global_approved = approved is not None
        method = "user_global_offset_approved" if global_approved else "vocal_onset_corrected"
        confidence = 0.78 if global_approved else min(0.72, float(event["confidence"]) + 0.03)
        asr_match = next((item for item in asr.get("segments", []) if item.get("phrase_id") == event["phrase_id"]), None)
        if asr_match and asr_match.get("classification") == "asr_matched":
            method = "local_asr_supported_by_waveform"
            confidence = max(confidence, 0.82)
        if any(item.get("user_action") == "correct_line_verified" for item in phrase_feedback):
            method = "human_verified"
            confidence = 0.95
        blockers = _calibrated_blockers(event, confidence, phrase_feedback)
        enriched = dict(event)
        enriched.update(
            {
                "original_boundary_timing": {"start": original_start, "end": original_end},
                "run14_corrected_timing": {"start": event["caption_start"], "end": event["caption_end"], "offset": event["offset_applied"]},
                "candidate_corrected_timing": {"start": candidate_start, "end": candidate_end, "offset": round(selected_offset, 3)},
                "user_approved_timing": {"approved": bool(method == "human_verified" or global_approved), "source": method if method in {"human_verified", "user_global_offset_approved"} else ""},
                "asr_timing": asr_match or {"classification": asr.get("classification", "asr_unavailable")},
                "final_review_timing": {"start": candidate_start, "end": candidate_end},
                "caption_start": candidate_start,
                "caption_end": candidate_end,
                "lip_sync_segment_start": candidate_start,
                "lip_sync_segment_end": candidate_end,
                "sync_method": method,
                "confidence": round(confidence, 3),
                "feedback_count": len(phrase_feedback),
                "needs_review": confidence < 0.82,
                "production_ready": bool(confidence >= 0.82 and not blockers),
                "offset_applied": round(selected_offset, 3),
                "blockers": blockers,
                "warning": "" if confidence >= 0.82 else "UNVERIFIED",
                "evidence": sorted(set(event.get("evidence", []) + ["offset_candidate_search", "sync_calibration"])),
            }
        )
        events.append(enriched)
    method_counts: dict[str, int] = {}
    confidence_counts = {"high": 0, "medium": 0, "low": 0}
    for event in events:
        method_counts[event["sync_method"]] = method_counts.get(event["sync_method"], 0) + 1
        if event["confidence"] >= 0.82:
            confidence_counts["high"] += 1
        elif event["confidence"] >= 0.7:
            confidence_counts["medium"] += 1
        else:
            confidence_counts["low"] += 1
    data = dict(base)
    data.update(
        {
            "version": "v1.0.7",
            "sync_method_counts": method_counts,
            "confidence_counts": confidence_counts,
            "high_confidence_phrase_count": confidence_counts["high"],
            "medium_confidence_phrase_count": confidence_counts["medium"],
            "low_confidence_phrase_count": confidence_counts["low"],
            "blocked_phrase_count": sum(1 for event in events if event["blockers"]),
            "offset_candidates_path": str(ENGINE_ROOT / "state" / "SYNC_OFFSET_CANDIDATES.json"),
            "selected_offset_seconds": round(selected_offset, 3),
            "selected_offset_source": "user_approved" if approved is not None else "best_review_candidate",
            "offset_candidates": candidates,
            "asr_alignment": asr,
            "feedback": feedback,
            "events": events,
            "warning": "Sync-calibrated review timing. Production captions and lip-sync still require human approval or verified ASR support.",
        }
    )
    BRAIN_TIMELINE_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return data


def build_lyric_meaning_emotion_map(auto_sync: dict[str, Any] | None = None, analysis: dict[str, Any] | None = None) -> dict[str, Any]:
    auto_sync = auto_sync or build_auto_sync()
    analysis = analysis or music_analysis()
    peaks = {int(item["time"]): item["rms"] for item in analysis.get("energy_curve", [])}
    rows = []
    for item in auto_sync["phrases"]:
        text = item["lyric_line"]
        mid = int((float(item["candidate_start"]) + float(item["candidate_end"])) / 2)
        energy = peaks.get(mid, 0.0)
        rows.append(
            {
                "phrase_id": item["phrase_id"],
                "phrase_index": item["phrase_index"],
                "original_burmese": item.get("source_original", ""),
                "approved_unicode": text,
                "pronunciation_helper": text,
                "rough_english_meaning": _rough_meaning(text),
                "emotional_meaning": _emotion_for_text(text, energy),
                "vocal_intensity": "high" if energy >= 0.22 else ("medium" if energy >= 0.13 else "low"),
                "music_energy": energy,
                "performance_direction": _performance_direction(text, energy),
                "shot_purpose": "carry emotional lyric beat without overexposing face",
                "caption_intent": "review lyric timing only",
                "lip_sync_importance": "candidate_after_brain_sync_review",
                "face_exposure_recommendation": "medium/wide/profile until identity and timing are approved",
                "evidence_labels": ["lyric_based", "music_energy_based", "director_inferred", "uncertain"],
            }
        )
    data = {"version": "v1.0.6", "phrases": rows}
    LYRIC_EMOTION_PATH.parent.mkdir(parents=True, exist_ok=True)
    LYRIC_EMOTION_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return data


def rebuild_caption_v5() -> dict[str, Any]:
    brain = build_brain_timeline()
    font = font_render_preview()
    CAPTION_V5_ROOT.mkdir(parents=True, exist_ok=True)
    rows = [_caption_row(event) for event in brain["events"] if not _instrumental_or_blocked(event)]
    (CAPTION_V5_ROOT / "CAPTIONS_REVIEW_BRAIN_SYNC.srt").write_text(_render_srt(rows), encoding="utf-8")
    (CAPTION_V5_ROOT / "CAPTIONS_REVIEW_BRAIN_SYNC.vtt").write_text(_render_vtt(rows), encoding="utf-8")
    (CAPTION_V5_ROOT / "CAPTIONS_REVIEW_BRAIN_SYNC.ass").write_text(_render_ass_v5(rows, font), encoding="utf-8")
    blockers = []
    if not font.get("render_test_passed"):
        blockers.append("FONT_RENDER_PREVIEW_FAILED")
    blockers.extend([f"PHRASE_{event['phrase_id']}_BRAIN_SYNC_LOW_CONFIDENCE" for event in brain["events"] if event["confidence"] < 0.75])
    blockers.append("APPROVED_UNICODE_REVIEW_REQUIRED")
    (CAPTION_V5_ROOT / "BRAIN_SYNC_STATUS.json").write_text(json.dumps(brain, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (CAPTION_V5_ROOT / "OFFSET_ANALYSIS.json").write_text(json.dumps(brain["offset"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (CAPTION_V5_ROOT / "CAPTION_BLOCKERS.json").write_text(json.dumps({"blockers": blockers}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"root": str(CAPTION_V5_ROOT), "brain": brain, "font": font, "blockers": blockers, "review_caption_count": len(rows)}


def rebuild_caption_v6() -> dict[str, Any]:
    brain = build_calibrated_brain_timeline()
    font = font_render_preview()
    CAPTION_V6_ROOT.mkdir(parents=True, exist_ok=True)
    rows = [_caption_row(event) for event in brain["events"] if not _instrumental_or_blocked(event)]
    (CAPTION_V6_ROOT / "CAPTIONS_REVIEW_SYNC_CALIBRATED.srt").write_text(_render_srt(rows), encoding="utf-8")
    (CAPTION_V6_ROOT / "CAPTIONS_REVIEW_SYNC_CALIBRATED.vtt").write_text(_render_vtt(rows), encoding="utf-8")
    (CAPTION_V6_ROOT / "CAPTIONS_REVIEW_SYNC_CALIBRATED.ass").write_text(_render_ass_calibrated(rows, font), encoding="utf-8")
    blockers = []
    if not font.get("render_test_passed"):
        blockers.append("FONT_RENDER_PREVIEW_FAILED")
    blockers.extend([f"PHRASE_{event['phrase_id']}_SYNC_CALIBRATION_LOW_CONFIDENCE" for event in brain["events"] if event["confidence"] < 0.82])
    blockers.append("PRODUCTION_REQUIRES_HUMAN_SYNC_APPROVAL")
    blockers.append("APPROVED_UNICODE_REVIEW_REQUIRED")
    (CAPTION_V6_ROOT / "SYNC_FEEDBACK_SUMMARY.json").write_text(json.dumps(brain["feedback"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (CAPTION_V6_ROOT / "OFFSET_CANDIDATES.json").write_text(json.dumps(brain["offset_candidates"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (CAPTION_V6_ROOT / "CAPTION_BLOCKERS.json").write_text(json.dumps({"blockers": blockers}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"root": str(CAPTION_V6_ROOT), "brain": brain, "font": font, "blockers": blockers, "review_caption_count": len(rows)}


def build_animatic_v14() -> dict[str, Any]:
    captions = rebuild_caption_v5()
    version = 14
    run_dir = ANIMATIC_ROOT / str(version)
    run_dir.mkdir(parents=True, exist_ok=True)
    master_duration = float(probe_media(MASTER_AUDIO)["duration"])
    frame_entries = frame_entries_for_full_song(list_storyboard_cards(), master_duration, run_dir)
    frames_txt = run_dir / "frames.txt"
    with frames_txt.open("w", encoding="utf-8") as handle:
        for image, duration in frame_entries:
            handle.write(f"file '{image}'\n")
            handle.write(f"duration {duration:.3f}\n")
        if frame_entries:
            handle.write(f"file '{frame_entries[-1][0]}'\n")
    clean = run_dir / "ANIMATIC.mp4"
    captioned = run_dir / "ANIMATIC_WITH_CAPTIONS_BRAIN_SYNC_REVIEW.mp4"
    review = run_dir / "ANIMATIC_REVIEW.mp4"
    log = run_dir / "BUILD_LOG.txt"
    if log.exists():
        log.unlink()
    commands = {}
    clean_args = [
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(frames_txt),
        "-i",
        str(MASTER_AUDIO),
        "-t",
        f"{master_duration:.3f}",
        "-vf",
        "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        str(clean),
    ]
    commands["clean"] = [ffmpeg_path(), *clean_args]
    _run_ffmpeg(clean_args, log)
    if captions["font"].get("render_test_passed") and captions["review_caption_count"]:
        cap_args = ["-y", "-i", str(clean), "-vf", f"subtitles={_escape_filter_path(CAPTION_V5_ROOT / 'CAPTIONS_REVIEW_BRAIN_SYNC.ass')}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "copy", str(captioned)]
        commands["captioned_brain_review"] = [ffmpeg_path(), *cap_args]
        _run_ffmpeg(cap_args, log)
    review_args = ["-y", "-i", str(clean), "-vf", "drawtext=text='BRAIN SYNC REVIEW - UNVERIFIED LOW CONFIDENCE':x=40:y=40:fontsize=42:fontcolor=white:box=1:boxcolor=black@0.65", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "copy", str(review)]
    commands["review"] = [ffmpeg_path(), *review_args]
    _run_ffmpeg(review_args, log)
    metadata = {name: _probe_optional(path) for name, path in {"clean": clean, "captioned_brain_review": captioned, "review": review}.items()}
    validation = duration_validation(master_duration, metadata.get("clean", {}).get("duration", 0))
    (run_dir / "BRAIN_SYNC_STATUS.json").write_text(json.dumps(captions["brain"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (run_dir / "OFFSET_ANALYSIS.json").write_text(json.dumps(captions["brain"]["offset"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (run_dir / "DURATION_VALIDATION.json").write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")
    (run_dir / "FONT_STATUS.json").write_text(json.dumps(captions["font"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (run_dir / "FFMPEG_COMMAND.json").write_text(json.dumps(commands, indent=2) + "\n", encoding="utf-8")
    (run_dir / "MEDIA_METADATA.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return {"version": version, "run_dir": str(run_dir), "metadata": metadata, "duration_validation": validation, "captions": captions}


def build_animatic_v15() -> dict[str, Any]:
    captions = rebuild_caption_v6()
    version = 15
    run_dir = ANIMATIC_ROOT / str(version)
    run_dir.mkdir(parents=True, exist_ok=True)
    master_duration = float(probe_media(MASTER_AUDIO)["duration"])
    frame_entries = frame_entries_for_full_song(list_storyboard_cards(), master_duration, run_dir)
    frames_txt = run_dir / "frames.txt"
    with frames_txt.open("w", encoding="utf-8") as handle:
        for image, duration in frame_entries:
            handle.write(f"file '{image}'\n")
            handle.write(f"duration {duration:.3f}\n")
        if frame_entries:
            handle.write(f"file '{frame_entries[-1][0]}'\n")
    clean = run_dir / "ANIMATIC.mp4"
    captioned = run_dir / "ANIMATIC_WITH_CAPTIONS_SYNC_CALIBRATED_REVIEW.mp4"
    review = run_dir / "ANIMATIC_REVIEW.mp4"
    log = run_dir / "BUILD_LOG.txt"
    if log.exists():
        log.unlink()
    commands = {}
    clean_args = [
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(frames_txt),
        "-i",
        str(MASTER_AUDIO),
        "-t",
        f"{master_duration:.3f}",
        "-vf",
        "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        str(clean),
    ]
    commands["clean"] = [ffmpeg_path(), *clean_args]
    _run_ffmpeg(clean_args, log)
    if captions["font"].get("render_test_passed") and captions["review_caption_count"]:
        cap_args = ["-y", "-i", str(clean), "-vf", f"subtitles={_escape_filter_path(CAPTION_V6_ROOT / 'CAPTIONS_REVIEW_SYNC_CALIBRATED.ass')}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "copy", str(captioned)]
        commands["captioned_sync_calibrated_review"] = [ffmpeg_path(), *cap_args]
        _run_ffmpeg(cap_args, log)
    review_args = ["-y", "-i", str(clean), "-vf", "drawtext=text='SYNC CALIBRATED REVIEW - LOW CONFIDENCE UNTIL APPROVED':x=40:y=40:fontsize=40:fontcolor=white:box=1:boxcolor=black@0.65", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "copy", str(review)]
    commands["review"] = [ffmpeg_path(), *review_args]
    _run_ffmpeg(review_args, log)
    metadata = {name: _probe_optional(path) for name, path in {"clean": clean, "captioned_sync_calibrated_review": captioned, "review": review}.items()}
    validation = duration_validation(master_duration, metadata.get("clean", {}).get("duration", 0))
    (run_dir / "SYNC_FEEDBACK_SUMMARY.json").write_text(json.dumps(captions["brain"]["feedback"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (run_dir / "OFFSET_CANDIDATES.json").write_text(json.dumps(captions["brain"]["offset_candidates"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (run_dir / "BRAIN_SYNC_STATUS.json").write_text(json.dumps(captions["brain"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (run_dir / "DURATION_VALIDATION.json").write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")
    (run_dir / "FONT_STATUS.json").write_text(json.dumps(captions["font"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (run_dir / "FFMPEG_COMMAND.json").write_text(json.dumps(commands, indent=2) + "\n", encoding="utf-8")
    (run_dir / "MEDIA_METADATA.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return {"version": version, "run_dir": str(run_dir), "metadata": metadata, "duration_validation": validation, "captions": captions}


def brain_lipsync_readiness() -> dict[str, Any]:
    brain = brain_timeline_status()
    rows = []
    for event in brain["events"]:
        if "WRONG_LINE_MARKER" in event.get("blockers", []):
            status = "blocked_on_wrong_line"
        elif event.get("confidence", 0) < 0.82 or event.get("sync_method") not in {"human_verified", "user_global_offset_approved", "local_asr_supported_by_waveform"}:
            status = "blocked_on_low_confidence_sync"
        elif event["blockers"]:
            status = "blocked_on_brain_sync"
        else:
            status = "ready_for_manual_infinitetalk_package"
        rows.append(
            {
                "shot_id": event["shot_id"],
                "phrase_id": event["phrase_id"],
                "sync_confidence": event["confidence"],
                "audio_segment": [event["lip_sync_segment_start"], event["lip_sync_segment_end"]],
                "face_suitability": "unknown_until_source_shot_review",
                "movement_risk": "unknown",
                "recommended_action": status,
            }
        )
    ready_count = sum(1 for row in rows if row["recommended_action"].startswith("ready"))
    blocked_count = len(rows) - ready_count
    return {
        "status": "blocked_on_brain_sync" if blocked_count else "ready_for_manual_infinitetalk_package",
        "rows": rows,
        "ready_count": ready_count,
        "blocked_count": blocked_count,
        "high_confidence_phrase_count": brain["high_confidence_phrase_count"],
        "low_confidence_phrase_count": brain["low_confidence_phrase_count"],
    }


def apply_caption_offset(seconds: float) -> dict[str, Any]:
    save_sync_feedback("shift_all_later" if seconds >= 0 else "shift_all_earlier", seconds=abs(seconds), note="CLI/user offset correction")
    return build_calibrated_brain_timeline()


def approve_global_caption_offset(seconds: float) -> dict[str, Any]:
    save_sync_feedback("approve_global_offset", seconds=seconds, note="User approved global sync-calibration offset")
    return build_calibrated_brain_timeline()


def run_local_asr_alignment() -> dict[str, Any]:
    from app.audio.asr.asr_health import asr_health

    health = asr_health()
    data = {
        "version": "v1.0.7",
        "classification": "asr_unavailable" if not health.get("available") else "asr_timing_useful_text_uncertain",
        "available": health.get("available"),
        "burmese_verified": health.get("burmese_verified"),
        "segments": [],
        "warnings": ["no ASR model was downloaded or installed", "singing Burmese ASR must be treated as evidence, not authority"],
        "providers": health.get("providers", []),
    }
    ASR_ALIGNMENT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ASR_ALIGNMENT_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return data


def local_asr_alignment_status() -> dict[str, Any]:
    if ASR_ALIGNMENT_PATH.exists():
        try:
            return json.loads(ASR_ALIGNMENT_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return run_local_asr_alignment()


def _caption_row(event: dict[str, Any]) -> dict[str, Any]:
    label = "UNVERIFIED" if event["confidence"] < 0.75 else event["sync_method"]
    text = f"P{event['phrase_index']} {label} {event['sync_method']} conf {event['confidence']:.2f} offset {event['offset_applied']:+.2f}s: {event['approved_unicode']}"
    return {"start": event["caption_start"], "end": event["caption_end"], "caption_text": text}


def _calibrated_blockers(event: dict[str, Any], confidence: float, phrase_feedback: list[dict[str, Any]]) -> list[str]:
    blockers = []
    if any(item.get("user_action") == "wrong_line" for item in phrase_feedback):
        blockers.append("WRONG_LINE_MARKER")
    if confidence < 0.82:
        blockers.append("LOW_CONFIDENCE_SYNC_CALIBRATION")
    return blockers


def _render_ass_calibrated(rows: list[dict[str, Any]], font: dict[str, Any]) -> str:
    font_name = font.get("selected_font") or "Arial"
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Burmese,{font_name},52,&H00FFFFFF,&H000000FF,&H00000000,&HAA000000,0,0,0,0,100,100,0,0,3,4,1,2,80,80,92,1
Style: Warning,{font_name},42,&H0000FFFF,&H000000FF,&H00000000,&HAA000000,1,0,0,0,100,100,0,0,3,2,1,8,60,60,48,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    end = rows[-1]["end"] if rows else 10
    events = [f"Dialogue: 1,0:00:00.00,{_ass(end)},Warning,,0,0,0,,SYNC CALIBRATED REVIEW - LOW CONFIDENCE UNTIL APPROVED"]
    for row in rows:
        events.append(f"Dialogue: 0,{_ass(row['start'])},{_ass(row['end'])},Burmese,,0,0,0,,{row['caption_text']}")
    return header + "\n".join(events) + "\n"


def _render_ass_v5(rows: list[dict[str, Any]], font: dict[str, Any]) -> str:
    font_name = font.get("selected_font") or "Arial"
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Burmese,{font_name},52,&H00FFFFFF,&H000000FF,&H00000000,&HAA000000,0,0,0,0,100,100,0,0,3,4,1,2,80,80,92,1
Style: Warning,{font_name},42,&H0000FFFF,&H000000FF,&H00000000,&HAA000000,1,0,0,0,100,100,0,0,3,2,1,8,60,60,48,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    end = rows[-1]["end"] if rows else 10
    events = [f"Dialogue: 1,0:00:00.00,{_ass(end)},Warning,,0,0,0,,BRAIN SYNC REVIEW - UNVERIFIED TIMING"]
    for row in rows:
        events.append(f"Dialogue: 0,{_ass(row['start'])},{_ass(row['end'])},Burmese,,0,0,0,,{row['caption_text']}")
    return header + "\n".join(events) + "\n"


def _instrumental_or_blocked(event: dict[str, Any]) -> bool:
    return "wrong_line" in event.get("blockers", [])


def _phrase_blockers(item: dict[str, Any], confidence: float) -> list[str]:
    blockers = []
    if confidence < 0.75:
        blockers.append("LOW_CONFIDENCE_ALIGNMENT")
    if item.get("likely_wrong_line"):
        blockers.append("WRONG_LINE_MARKER")
    return blockers


def _song_sections(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    duration = float(analysis.get("duration") or 0)
    return [
        {"section": "intro", "start": 0, "end": 32.18, "type": "instrumental_or_pre_vocal"},
        {"section": "vocal_phrase_region", "start": 32.18, "end": 133.2, "type": "vocal"},
        {"section": "outro_or_missing_later_vocals", "start": 133.2, "end": duration, "type": "instrumental_or_unmapped"},
    ]


def _section_for_time(start: float, analysis: dict[str, Any]) -> str:
    for section in _song_sections(analysis):
        if section["start"] <= start <= section["end"]:
            return section["section"]
    return "unknown"


def _card_for_time(cards: list[dict[str, Any]], start: float, end: float) -> dict[str, Any]:
    midpoint = (start + end) / 2
    for card in cards:
        try:
            from app.services.director_workspace_service import tc_seconds

            if tc_seconds(card["timecode_start"]) <= midpoint <= tc_seconds(card["timecode_end"]):
                return card
        except Exception:
            continue
    return cards[-1] if cards else {}


def _rough_meaning(text: str) -> str:
    if any(word in text for word in ["အလွမ်း", "ဆွေး", "လွမ်း"]):
        return "longing, grief, and remembered love"
    if any(word in text for word in ["အမှောင်", "ည", "အရိပ်", "မွောင်"]):
        return "darkness, silence, and emotional isolation"
    if any(word in text for word in ["အနမ်း", "အချစ်"]):
        return "lost intimacy and love"
    return "heartbreak memory and emotional pressure"


def _emotion_for_text(text: str, energy: float) -> str:
    base = _rough_meaning(text)
    if energy >= 0.22:
        return f"heightened {base}"
    if energy <= 0.1:
        return f"restrained {base}"
    return base


def _performance_direction(text: str, energy: float) -> str:
    if energy >= 0.22:
        return "controlled emotional pressure, stronger breath and torso tension"
    return "restrained expression, low arms, grounded stillness with small controlled movement"
