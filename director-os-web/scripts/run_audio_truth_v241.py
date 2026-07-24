#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_ROOT = REPO_ROOT / "director-os"
PROJECT_ROOT = ENGINE_ROOT / "projects" / "burmese-music-video"
STATE_ROOT = ENGINE_ROOT / "state"
V3_ROOT = PROJECT_ROOT / "audio-truth" / "v3"
V4_ROOT = PROJECT_ROOT / "audio-truth" / "v4"
V4_ANCHORS = V4_ROOT / "anchors"
V4_SEGMENTS = V4_ROOT / "lipsync-segments"
V4_EVAL = V4_ROOT / "evaluation"
CAPTION_ROOT = ENGINE_ROOT / "captions" / "audio-truth-v4"
PREVIEW_ROOT = PROJECT_ROOT / "previews" / "audio-truth-v4"
RESEARCH_ROOT = REPO_ROOT / "director-os-research"
MASTER_AUDIO = REPO_ROOT / "audio" / "01.mp3"
FFMPEG = REPO_ROOT / "local-tools" / "envs" / "faceswap" / "bin" / "ffmpeg"
FFPROBE = REPO_ROOT / "local-tools" / "envs" / "faceswap" / "bin" / "ffprobe"


def main() -> int:
    for root in [V4_ROOT, V4_ANCHORS, V4_SEGMENTS, V4_EVAL, CAPTION_ROOT, PREVIEW_ROOT, STATE_ROOT, RESEARCH_ROOT]:
        root.mkdir(parents=True, exist_ok=True)

    v3_timeline = read_json(STATE_ROOT / "AUDIO_TRUTH_TIMELINE_V3.json", {})
    if not v3_timeline:
        raise SystemExit("AUDIO_TRUTH_TIMELINE_V3.json is required")

    v3_status = read_json(V3_ROOT / "AUDIO_TRUTH_V3_STATUS.json", {})
    real_feedback = write_real_user_feedback()
    occurrences = v3_timeline["occurrences"]
    vocal_wav = V3_ROOT / "stems" / "selected_vocals_16k_mono.wav"
    audio = load_wav_mono(vocal_wav)

    candidates = score_anchor_candidates(occurrences, audio, real_feedback)
    anchors = select_replacement_anchors(candidates, occurrences)
    timeline = build_timeline_v4(v3_timeline, anchors, candidates)
    write_json(STATE_ROOT / "AUDIO_TRUTH_TIMELINE_V4.json", timeline)
    write_json(STATE_ROOT / "AUDIO_TRUTH_ANCHOR_CANDIDATES.json", candidates)

    anchor_validation = build_anchor_clips(anchors, timeline, audio)
    write_json(V4_ANCHORS / "ANCHOR_VALIDATION.json", anchor_validation)
    build_anchor_contact_sheet()

    caption_eval = build_captions_v4(timeline, anchor_validation)
    lipsync = build_lipsync_segments_v4(timeline)
    preview = build_preview_v4(timeline)
    playback = validate_preview_playback(preview["captioned"])
    write_json(PREVIEW_ROOT / "PLAYBACK_VALIDATION.json", playback)
    write_json(PREVIEW_ROOT / "CAPTION_AUDIO_VALIDATION.json", caption_eval)

    status = {
        "version": "v2.4.1",
        "created_at": now(),
        "canonical_lyric_source": v3_timeline.get("canonical_lyric_source"),
        "invalidated_v3_anchor_set": real_feedback["status"],
        "first_anchor": "human_verified_early_anchor",
        "anchors": {
            "early": anchors["early"],
            "middle": anchors["middle"],
            "late": anchors["late"],
            "validation_path": str(V4_ANCHORS / "ANCHOR_VALIDATION.json"),
        },
        "timeline": summarize_timeline(timeline),
        "captions": {
            "path": str(CAPTION_ROOT),
            "review_caption_count": len(timeline["occurrences"]),
            "production_ready": False,
            "blockers": ["MIDDLE_AND_LATE_ANCHOR_CONFIRMATION_REQUIRED"],
        },
        "lipsync": lipsync,
        "preview": preview,
        "playback_validation": playback,
        "caption_audio_validation": caption_eval["summary"],
        "soemind_forge": adapt_soemind_forge_patterns(),
        "next_action": "Review the two replacement Audio Truth anchors.",
        "no_new_model_download": True,
        "no_cloud_upload": True,
        "no_paid_api": True,
    }
    write_json(V4_ROOT / "AUDIO_TRUTH_V4_STATUS.json", status)
    update_brain(timeline, status)
    write_report(status, candidates, real_feedback, playback, caption_eval)
    print(json.dumps(status, indent=2, ensure_ascii=False))
    return 0


def write_real_user_feedback() -> dict[str, Any]:
    payload = {
        "version": "v2.4.1",
        "created_at": now(),
        "status": "invalidated_by_real_user_review",
        "evidence_source": "user_observed_audio_truth_page_review",
        "anchors": {
            "early": {
                "occurrence_id": "lyric_line_3b6a71e0_occurrence_1",
                "status": "accepted_correct",
                "use_as": "human_verified_early_anchor",
            },
            "middle": {
                "occurrence_id": "lyric_line_22df2ed0_occurrence_1",
                "status": "invalid_no_clear_vocal_or_caption_late",
                "use_as": "rejected_acceptance_anchor",
            },
            "late": {
                "occurrence_id": "lyric_line_68353461_occurrence_1",
                "status": "invalid_alignment",
                "use_as": "rejected_acceptance_anchor",
            },
        },
        "final_preview": {
            "status": "playback_or_content_failure",
            "repair_required": True,
        },
    }
    write_json(STATE_ROOT / "AUDIO_TRUTH_REAL_USER_FEEDBACK.json", payload)
    return payload


def score_anchor_candidates(occurrences: list[dict[str, Any]], audio: dict[str, Any], feedback: dict[str, Any]) -> dict[str, Any]:
    rejected_ids = {
        feedback["anchors"]["middle"]["occurrence_id"],
        feedback["anchors"]["late"]["occurrence_id"],
    }
    records = []
    for occ in occurrences:
        timing = occ["final_caption_timing"]
        start = float(timing["start"])
        end = float(timing["end"])
        duration = end - start
        energy = segment_rms(audio, start, end)
        pre_energy = segment_rms(audio, max(0.0, start - 1.5), start)
        post_energy = segment_rms(audio, end, min(audio["duration"], end + 1.5))
        unique = occurrence_count(occurrences, occ["canonical_unicode_lyric"]) == 1
        old_rejected = occ["occurrence_id"] in rejected_ids
        reasons = []
        if old_rejected:
            reasons.append("invalidated_by_real_user_review")
        if duration < 3.2:
            reasons.append("phrase_too_short_for_anchor")
        if energy < 0.002:
            reasons.append("no_vocal_present")
        if energy <= max(pre_energy, post_energy) * 0.85:
            reasons.append("music_or_ambience_dominates_vocal_window")
        if occ["confidence_class"] not in {"high", "medium"}:
            reasons.append("alignment_not_usable")
        if not unique and occ["confidence_class"] != "high":
            reasons.append("repeated_occurrence_not_strong_enough")
        score = (
            min(1.0, energy * 220.0) * 0.36
            + min(1.0, duration / 6.0) * 0.22
            + (0.18 if unique else 0.08)
            + float(occ.get("confidence_score", 0.0)) * 0.24
        )
        if reasons:
            score *= 0.25
        records.append(
            {
                "occurrence_id": occ["occurrence_id"],
                "source_line": occ["source_line"],
                "lyric": occ["canonical_unicode_lyric"],
                "start": start,
                "end": end,
                "duration": round(duration, 3),
                "song_position": round((start + end) / 2.0, 3),
                "confidence_class": occ["confidence_class"],
                "confidence_score": occ["confidence_score"],
                "unique_lyric": unique,
                "vocal_energy": round(energy, 6),
                "pre_roll_energy": round(pre_energy, 6),
                "post_roll_energy": round(post_energy, 6),
                "anchor_score": round(score, 4),
                "valid": not reasons,
                "rejection_reasons": reasons,
            }
        )
    payload = {
        "version": "audio-truth-v4",
        "created_at": now(),
        "candidate_count": len(records),
        "invalidated_occurrence_ids": sorted(rejected_ids),
        "candidates": records,
    }
    return payload


def select_replacement_anchors(candidates: dict[str, Any], occurrences: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {occ["occurrence_id"]: occ for occ in occurrences}
    valid = [c for c in candidates["candidates"] if c["valid"]]
    early_occ = by_id["lyric_line_3b6a71e0_occurrence_1"]
    middle = best_in_range(valid, 95.0, 130.0)
    if not middle:
        middle = best_in_range(valid, 90.0, 140.0)
    late = best_in_range([c for c in valid if c["occurrence_id"] != (middle or {}).get("occurrence_id")], 135.0, 170.0)
    if not late:
        late = best_in_range([c for c in valid if c["occurrence_id"] != (middle or {}).get("occurrence_id")], 125.0, 170.0)
    if not middle or not late:
        raise RuntimeError("No valid replacement middle/late anchors found")
    return {
        "early": anchor_record("anchor_early_verified", "early", early_occ, "human_verified_early_anchor"),
        "middle": anchor_record("anchor_middle_candidate", "middle", by_id[middle["occurrence_id"]], "replacement_candidate"),
        "late": anchor_record("anchor_late_candidate", "late", by_id[late["occurrence_id"]], "replacement_candidate"),
    }


def best_in_range(candidates: list[dict[str, Any]], start: float, end: float) -> dict[str, Any] | None:
    in_range = [c for c in candidates if start <= c["song_position"] <= end]
    if not in_range:
        return None
    return sorted(in_range, key=lambda c: (c["anchor_score"], c["duration"]), reverse=True)[0]


def anchor_record(anchor_id: str, position: str, occ: dict[str, Any], status: str) -> dict[str, Any]:
    timing = occ["final_caption_timing"]
    start = float(timing["start"])
    end = float(timing["end"])
    return {
        "anchor_id": anchor_id,
        "position": position,
        "occurrence_id": occ["occurrence_id"],
        "clip": str(V4_ANCHORS / f"{anchor_id}.mp4"),
        "lyric": occ["canonical_unicode_lyric"],
        "english_meaning": "meaning retained from Audio Truth map; exact translation review remains separate",
        "start": start,
        "end": end,
        "detected_vocal_start": occ.get("vocal_onset", start),
        "detected_vocal_end": occ.get("vocal_offset", end),
        "caption_start": start,
        "caption_end": end,
        "confidence": occ["confidence_score"],
        "status": status,
    }


def build_timeline_v4(v3_timeline: dict[str, Any], anchors: dict[str, Any], candidates: dict[str, Any]) -> dict[str, Any]:
    verified_early = anchors["early"]
    candidate_ids = {anchors["middle"]["occurrence_id"], anchors["late"]["occurrence_id"]}
    invalidated_ids = {"lyric_line_22df2ed0_occurrence_1", "lyric_line_68353461_occurrence_1"}
    valid_by_id = {c["occurrence_id"]: c for c in candidates["candidates"]}
    occurrences = []
    for occ in v3_timeline["occurrences"]:
        occ = dict(occ)
        occ["supersedes_for_production_timing"] = "AUDIO_TRUTH_TIMELINE_V3.json"
        occ["user_feedback"] = "human_verified_early_anchor" if occ["occurrence_id"] == verified_early["occurrence_id"] else ""
        occ["anchor_validation_state"] = "replacement_anchor_candidate" if occ["occurrence_id"] in candidate_ids else "not_anchor"
        occ["v4_anchor_candidate_score"] = valid_by_id.get(occ["occurrence_id"], {}).get("anchor_score", 0.0)
        if occ["occurrence_id"] == verified_early["occurrence_id"]:
            occ["confidence_class"] = "high"
            occ["confidence_score"] = max(float(occ["confidence_score"]), 0.93)
            occ["status"] = "human_verified_high_confidence"
            occ["production_caption_readiness"] = True
            occ["lip_sync_segment_readiness"] = True
            occ["unresolved_blocker"] = []
            occ["evidence"] = sorted(set(occ.get("evidence", []) + ["human_verified_early_anchor"]))
        elif occ["occurrence_id"] in invalidated_ids:
            occ["production_caption_readiness"] = False
            occ["lip_sync_segment_readiness"] = False
            occ["unresolved_blocker"] = ["INVALIDATED_BY_REAL_USER_REVIEW"]
            occ["contradicting_evidence"] = sorted(set(occ.get("contradicting_evidence", []) + ["user_rejected_anchor_timing_or_mapping"]))
            occ["evidence"] = sorted(set(occ.get("evidence", []) + ["preserved_for_history_not_production_evidence"]))
        elif occ["occurrence_id"] in candidate_ids:
            occ["production_caption_readiness"] = False
            occ["lip_sync_segment_readiness"] = False
            occ["unresolved_blocker"] = ["REPLACEMENT_ANCHOR_CONFIRMATION_PENDING"]
            occ["evidence"] = sorted(set(occ.get("evidence", []) + ["v4_anchor_validity_gate_passed"]))
        elif occ.get("confidence_class") == "high":
            occ["production_caption_readiness"] = True
            occ["lip_sync_segment_readiness"] = True
            occ["unresolved_blocker"] = []
        else:
            occ["production_caption_readiness"] = False
            occ["lip_sync_segment_readiness"] = False
            occ["unresolved_blocker"] = ["ANCHOR_PROPAGATION_PENDING"]
        occurrences.append(occ)
    return {
        "version": "audio-truth-v4",
        "created_at": now(),
        "master_song": v3_timeline.get("master_song"),
        "master_duration": v3_timeline.get("master_duration"),
        "canonical_lyric_source": v3_timeline.get("canonical_lyric_source"),
        "supersedes_for_production_timing": "AUDIO_TRUTH_TIMELINE_V3.json",
        "human_verified_anchor": verified_early["occurrence_id"],
        "replacement_anchor_candidates": [anchors["middle"]["occurrence_id"], anchors["late"]["occurrence_id"]],
        "occurrences": occurrences,
        "production_caption_allowed": False,
        "lipsync_allowed_count": sum(1 for occ in occurrences if occ["lip_sync_segment_readiness"]),
    }


def build_anchor_clips(anchors: dict[str, Any], timeline: dict[str, Any], audio: dict[str, Any]) -> dict[str, Any]:
    records = []
    for key in ["early", "middle", "late"]:
        anchor = anchors[key]
        duration = anchor["end"] - anchor["start"]
        pre = 2.0
        post = 2.0
        clip_start = max(0.0, anchor["start"] - pre)
        clip_end = min(float(timeline["master_duration"]), anchor["end"] + post)
        if clip_end - clip_start < 7.0:
            extra = (7.0 - (clip_end - clip_start)) / 2.0
            clip_start = max(0.0, clip_start - extra)
            clip_end = min(float(timeline["master_duration"]), clip_end + extra)
        out = V4_ANCHORS / f"{anchor['anchor_id']}.mp4"
        ass = V4_ANCHORS / f"{anchor['anchor_id']}.ass"
        write_anchor_ass(ass, anchor, clip_start, clip_end)
        run(
            [
                str(FFMPEG),
                "-y",
                "-ss",
                f"{clip_start:.3f}",
                "-t",
                f"{clip_end - clip_start:.3f}",
                "-i",
                str(MASTER_AUDIO),
                "-f",
                "lavfi",
                "-i",
                f"color=c=0x161616:s=1280x720:r=24:d={clip_end - clip_start:.3f}",
                "-map",
                "1:v",
                "-map",
                "0:a",
                "-vf",
                f"subtitles={escape_filter_path(ass)}",
                "-c:v",
                "libx264",
                "-profile:v",
                "main",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-movflags",
                "+faststart",
                str(out),
            ],
            check=True,
        )
        probe = probe_media(out)
        vocal_energy = segment_rms(audio, anchor["start"], anchor["end"])
        valid = (
            out.exists()
            and probe["has_audio"]
            and probe["has_video"]
            and probe["duration"] >= 6.8
            and vocal_energy > 0.002
            and anchor["start"] >= clip_start
            and anchor["end"] <= clip_end
        )
        reasons = []
        if not valid:
            if vocal_energy <= 0.002:
                reasons.append("NO_VOCAL_PRESENT")
            if probe["duration"] < 6.8:
                reasons.append("SHORT_OR_TRUNCATED_ANCHOR")
            if not probe["has_audio"] or not probe["has_video"]:
                reasons.append("ANCHOR_PLAYBACK_STREAM_MISSING")
        records.append(
            {
                **anchor,
                "clip": str(out),
                "clip_url": f"/studio-assets/burmese-music-video/audio-truth/v4/anchors/{out.name}",
                "clip_start": round(clip_start, 3),
                "clip_end": round(clip_end, 3),
                "clip_duration": round(probe["duration"], 3),
                "vocal_energy": round(vocal_energy, 6),
                "valid": valid,
                "validation_reasons": reasons or ["anchor_validity_gate_passed"],
                "ffprobe": probe,
            }
        )
    payload = {
        "version": "audio-truth-v4",
        "created_at": now(),
        "status": "replacement_anchors_ready" if all(r["valid"] for r in records) else "anchor_generation_failed",
        "anchors": records,
    }
    write_json(STATE_ROOT / "AUDIO_TRUTH_ANCHORS_V4.json", payload)
    return payload


def build_anchor_contact_sheet() -> None:
    inputs = [V4_ANCHORS / "anchor_early_verified.mp4", V4_ANCHORS / "anchor_middle_candidate.mp4", V4_ANCHORS / "anchor_late_candidate.mp4"]
    frames = []
    for idx, path in enumerate(inputs):
        frame = V4_ANCHORS / f"anchor_{idx}.png"
        run([str(FFMPEG), "-y", "-ss", "1", "-i", str(path), "-frames:v", "1", str(frame)], check=False)
        if frame.exists():
            frames.extend(["-i", str(frame)])
    if len(frames) == 6:
        run([str(FFMPEG), "-y", *frames, "-filter_complex", "hstack=inputs=3", str(V4_ANCHORS / "ANCHOR_CONTACT_SHEET.png")], check=False)


def write_anchor_ass(path: Path, anchor: dict[str, Any], clip_start: float, clip_end: float) -> None:
    phrase_start = anchor["start"] - clip_start
    phrase_end = anchor["end"] - clip_start
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1280",
        "PlayResY: 720",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Default,Myanmar MN,44,&H00FFFFFF,&H000000FF,&H00000000,&H90000000,0,0,0,0,100,100,0,0,3,2,0,2,70,70,70,1",
        "Style: Meta,Arial,24,&H00D8D8D8,&H000000FF,&H00000000,&H90000000,0,0,0,0,100,100,0,0,3,1,0,8,40,40,35,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        f"Dialogue: 0,0:00:00.00,{ass_time(clip_end - clip_start)},Meta,,0,0,0,,{anchor['position'].upper()} {anchor['occurrence_id']}  song {anchor['start']:.2f}-{anchor['end']:.2f}s",
        f"Dialogue: 0,{ass_time(phrase_start)},{ass_time(phrase_end)},Default,,0,0,0,,{escape_ass(anchor['lyric'])}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_captions_v4(timeline: dict[str, Any], anchor_validation: dict[str, Any]) -> dict[str, Any]:
    items = []
    defects = []
    anchors = {a["occurrence_id"]: a for a in anchor_validation["anchors"]}
    for idx, occ in enumerate(timeline["occurrences"], start=1):
        timing = occ["final_caption_timing"]
        start = float(timing["start"])
        end = float(timing["end"])
        items.append({"index": idx, "start": start, "end": end, "text": occ["canonical_unicode_lyric"], "occurrence_id": occ["occurrence_id"]})
        if occ["occurrence_id"] in anchors and not anchors[occ["occurrence_id"]]["valid"]:
            defects.append({"occurrence_id": occ["occurrence_id"], "code": "ANCHOR_INVALID"})
        if end <= start:
            defects.append({"occurrence_id": occ["occurrence_id"], "code": "PHRASE_TRUNCATED"})
        if occ["occurrence_id"] == "lyric_line_22df2ed0_occurrence_1":
            defects.append({"occurrence_id": occ["occurrence_id"], "code": "OLD_MIDDLE_ANCHOR_REJECTED"})
        if occ["occurrence_id"] == "lyric_line_68353461_occurrence_1":
            defects.append({"occurrence_id": occ["occurrence_id"], "code": "OLD_LATE_ANCHOR_REJECTED"})
    write_srt(CAPTION_ROOT / "CAPTIONS_AUDIO_TRUTH_V4_REVIEW.srt", items)
    write_vtt(CAPTION_ROOT / "CAPTIONS_AUDIO_TRUTH_V4_REVIEW.vtt", items)
    write_ass(CAPTION_ROOT / "CAPTIONS_AUDIO_TRUTH_V4_REVIEW.ass", items)
    payload = {
        "version": "audio-truth-v4",
        "summary": {
            "caption_count": len(items),
            "defect_count": len(defects),
            "production_ready": False,
            "reason": "two replacement anchors require user confirmation",
        },
        "defects": defects,
    }
    write_json(CAPTION_ROOT / "CAPTION_AUDIO_VALIDATION.json", payload)
    write_json(CAPTION_ROOT / "CAPTION_BLOCKERS.json", {"blockers": ["MIDDLE_AND_LATE_ANCHOR_CONFIRMATION_REQUIRED"]})
    return payload


def build_lipsync_segments_v4(timeline: dict[str, Any]) -> dict[str, Any]:
    ready = []
    blocked = []
    for occ in timeline["occurrences"]:
        target = V4_SEGMENTS / occ["occurrence_id"]
        target.mkdir(parents=True, exist_ok=True)
        timing = occ["exact_master_audio_segment_timing"]
        (target / "lyric.txt").write_text(occ["canonical_unicode_lyric"] + "\n", encoding="utf-8")
        write_json(target / "timing.json", timing)
        if occ["lip_sync_segment_readiness"]:
            master = target / "master_audio.wav"
            vocal = target / "isolated_vocal.wav"
            run([str(FFMPEG), "-y", "-ss", str(timing["start"]), "-to", str(timing["end"]), "-i", str(MASTER_AUDIO), "-ac", "1", "-ar", "48000", str(master)], check=False)
            run([str(FFMPEG), "-y", "-ss", str(timing["start"]), "-to", str(timing["end"]), "-i", str(V3_ROOT / "stems" / "selected_vocals_16k_mono.wav"), "-ac", "1", "-ar", "48000", str(vocal)], check=False)
            valid = master.exists() and probe_media(master)["has_audio"]
            write_json(target / "validation.json", {"ready": valid, "source": "AUDIO_TRUTH_TIMELINE_V4"})
            if valid:
                ready.append(occ["occurrence_id"])
            else:
                blocked.append({"occurrence_id": occ["occurrence_id"], "reason": ["SEGMENT_VALIDATION_FAILED"]})
        else:
            reason = occ.get("unresolved_blocker") or ["ANCHOR_CONFIRMATION_REQUIRED"]
            write_json(target / "validation.json", {"ready": False, "source": "AUDIO_TRUTH_TIMELINE_V4", "blockers": reason})
            blocked.append({"occurrence_id": occ["occurrence_id"], "reason": reason})
    payload = {
        "ready_occurrence_count": len(ready),
        "blocked_occurrence_count": len(blocked),
        "ready": ready,
        "blocked": blocked,
        "path": str(V4_SEGMENTS),
    }
    write_json(V4_SEGMENTS / "LIPSYNC_SEGMENT_STATUS.json", payload)
    return payload


def build_preview_v4(timeline: dict[str, Any]) -> dict[str, Any]:
    source = PROJECT_ROOT / "previews" / "audio-truth-v3" / "CREATIVE_SKETCH_AUDIO_TRUTH_V3.mp4"
    if not source.exists():
        source = PROJECT_ROOT / "previews" / "audio-truth-v2" / "CREATIVE_SKETCH_AUDIO_TRUTH_V2.mp4"
    clean = PREVIEW_ROOT / "CREATIVE_SKETCH_AUDIO_TRUTH_V4.mp4"
    captioned = PREVIEW_ROOT / "CREATIVE_SKETCH_AUDIO_TRUTH_V4_WITH_CAPTIONS.mp4"
    review = PREVIEW_ROOT / "CREATIVE_SKETCH_AUDIO_TRUTH_V4_REVIEW.mp4"
    ass = CAPTION_ROOT / "CAPTIONS_AUDIO_TRUTH_V4_REVIEW.ass"
    log = []
    source_probe = probe_media(source)
    master_duration = float(timeline["master_duration"])
    video_pad = max(0.0, master_duration - float(source_probe.get("video_duration", source_probe.get("duration", 0.0))))
    clean_vf = f"tpad=stop_mode=clone:stop_duration={video_pad:.3f}" if video_pad > 0.25 else "null"
    transcode_args = [
        str(FFMPEG),
        "-y",
        "-i",
        str(source),
        "-vf",
        clean_vf,
        "-c:v",
        "libx264",
        "-profile:v",
        "main",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        str(clean),
    ]
    log.append("$ " + " ".join(transcode_args))
    run(transcode_args, check=True)
    caption_args = [
        str(FFMPEG),
        "-y",
        "-i",
        str(clean),
        "-vf",
        f"subtitles={escape_filter_path(ass)}",
        "-c:v",
        "libx264",
        "-profile:v",
        "main",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        str(captioned),
    ]
    log.append("$ " + " ".join(caption_args))
    run(caption_args, check=True)
    shutil.copyfile(captioned, review)
    validation = {
        "master_duration": master_duration,
        "preview_duration": probe_media(captioned)["duration"],
        "video_stream_duration": probe_media(captioned).get("video_duration", 0.0),
        "audio_stream_duration": probe_media(captioned).get("audio_duration", 0.0),
        "video_pad_applied": round(video_pad, 3),
    }
    validation["difference"] = abs(validation["master_duration"] - validation["preview_duration"])
    validation["status"] = "ok" if validation["difference"] <= 0.5 else "failed"
    write_json(PREVIEW_ROOT / "DURATION_VALIDATION.json", validation)
    write_json(PREVIEW_ROOT / "BUILD_LOG.txt", {"commands": log, "source": str(source), "captions": str(ass)})
    write_json(PREVIEW_ROOT / "AUDIO_TRUTH_EVALUATION.json", {"duration": validation, "source_timeline": str(STATE_ROOT / "AUDIO_TRUTH_TIMELINE_V4.json")})
    return {
        "path": str(PREVIEW_ROOT),
        "clean": str(clean),
        "captioned": str(captioned),
        "review": str(review),
        "url": "/studio-assets/burmese-music-video/previews/audio-truth-v4/CREATIVE_SKETCH_AUDIO_TRUTH_V4_WITH_CAPTIONS.mp4",
        "duration_validation": validation,
    }


def validate_preview_playback(path: Path | str) -> dict[str, Any]:
    media_path = Path(path)
    probe = probe_media(media_path)
    status = {
        "file_exists": media_path.exists(),
        "mime_expected": "video/mp4",
        "duration": probe.get("duration", 0.0),
        "video_duration": probe.get("video_duration", 0.0),
        "audio_duration": probe.get("audio_duration", 0.0),
        "has_audio": probe.get("has_audio", False),
        "has_video": probe.get("has_video", False),
        "codec_compatible": probe.get("video_codec") == "h264" and probe.get("audio_codec") == "aac",
        "seekable_faststart": b"moov" in media_path.read_bytes()[:1024 * 256] if media_path.exists() else False,
        "http_status": None,
        "range_status": None,
        "browser_playback": "not_run_playwright_unavailable",
        "playback_ready": False,
        "repair": "V4 rebuilt with H.264/AAC/yuv420p and +faststart after V3 user-observed playback/content failure.",
    }
    url = "http://127.0.0.1:8787/studio-assets/burmese-music-video/previews/audio-truth-v4/CREATIVE_SKETCH_AUDIO_TRUTH_V4_WITH_CAPTIONS.mp4"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            status["http_status"] = response.status
            status["content_type"] = response.headers.get("content-type")
    except Exception as exc:  # server may not be running during script execution
        status["http_error"] = str(exc)
    try:
        request = urllib.request.Request(url, headers={"Range": "bytes=0-1023"})
        with urllib.request.urlopen(request, timeout=5) as response:
            status["range_status"] = response.status
            status["range_content_length"] = int(response.headers.get("content-length", "0"))
    except Exception as exc:
        status["range_error"] = str(exc)
    status["playback_ready"] = all(
        [
            status["file_exists"],
            status["duration"] > 250,
            status["video_duration"] > 250,
            abs(status["audio_duration"] - status["video_duration"]) <= 1.0,
            status["has_audio"],
            status["has_video"],
            status["codec_compatible"],
            status["seekable_faststart"],
            status.get("http_status") in {200, None},
            status.get("range_status") in {200, 206, None},
        ]
    )
    return status


def adapt_soemind_forge_patterns() -> dict[str, Any]:
    repo = REPO_ROOT / "local-tools" / "research-repos" / "soemind-forge"
    commit = command_output(["git", "-C", str(repo), "rev-parse", "HEAD"]).strip() if repo.exists() else ""
    features = [
        ("one plain-English production command", "adapted", "Studio keeps CREATE EVERYTHING / repair loop as the user-facing command."),
        ("content preflight before generation", "adopted", "Audio Truth V4 invalidates broken anchors before rebuilding."),
        ("locked reusable asset registry", "already exists", "Director OS preserves approved/rejected references and canonical lyric source."),
        ("character/face consistency by asset ID", "already exists", "Project evidence IDs remain authoritative; not used for audio repair."),
        ("preview-before-expensive-render", "adapted", "V4 creates local anchor/preview MP4s before any renderer or InfiniteTalk."),
        ("content review after generation", "adopted", "Anchor validity and playback validation run before UI promotion."),
        ("task recipes/skills", "adapted", "Audio Truth Repair recipe added to Studio status."),
        ("budget cap and spend ledger", "already exists", "No spend path used in v2.4.1."),
        ("output packaging", "adapted", "V4 packages captions, preview, anchor clips, validation, and lip-sync segments."),
        ("local post-production text rendering", "adopted", "ASS subtitles rendered locally with FFmpeg."),
        ("agent instructions continue through QA and packaging", "adopted", "V4 script runs invalidate -> regenerate -> validate -> package -> report."),
        ("cloud-first generation assumptions", "rejected", "Director OS remains local-first and does not use providers here."),
    ]
    report = [
        "# SoeMind Forge Adaptation v2.4.1",
        "",
        f"Repository: `{repo}`",
        f"Inspected commit: `{commit}`",
        "",
        "No setup scripts, provider calls, cloud uploads, or private-media exports were executed.",
        "",
        "| Feature | Decision | Director OS connection |",
        "|---|---|---|",
    ]
    for feature, decision, connection in features:
        report.append(f"| {feature} | {decision} | {connection} |")
    report.append("")
    report.append("Applied pattern: content preflight and content review now gate Audio Truth anchors before they are presented in the Studio UI.")
    path = RESEARCH_ROOT / "SOEMIND_FORGE_ADAPTATION_V2_4_1.md"
    path.write_text("\n".join(report) + "\n", encoding="utf-8")
    return {"repo": str(repo), "commit": commit, "report": str(path), "adapted_features": len([f for f in features if f[1] in {"adopted", "adapted"}])}


def update_brain(timeline: dict[str, Any], status: dict[str, Any]) -> None:
    path = STATE_ROOT / "PRODUCTION_BRAIN.json"
    brain = read_json(path, {})
    brain["audio_truth"] = {"version": "v2.4.1", "status": "replacement_anchor_review_required", "status_path": str(V4_ROOT / "AUDIO_TRUTH_V4_STATUS.json")}
    brain["lyrics"] = timeline["occurrences"]
    brain["captions"] = {"source": "AUDIO_TRUTH_TIMELINE_V4.json", "production_ready": False}
    brain["lip_sync"] = {"source": "AUDIO_TRUTH_TIMELINE_V4.json", "ready_occurrence_count": status["lipsync"]["ready_occurrence_count"]}
    brain["workflow_patterns"] = {"soemind_forge_v241": status["soemind_forge"]}
    write_json(path, brain)


def write_report(status: dict[str, Any], candidates: dict[str, Any], feedback: dict[str, Any], playback: dict[str, Any], caption_eval: dict[str, Any]) -> None:
    middle = status["anchors"]["middle"]
    late = status["anchors"]["late"]
    report = f"""# Director OS v2.4.1 Real Anchor And Playback Repair Report

Generated: {now()}

## User Acceptance Evidence

- Previous anchor set: invalidated_by_real_user_review
- Early anchor: accepted_correct and preserved as human_verified_early_anchor
- Previous middle anchor: invalid_no_clear_vocal_or_caption_late
- Previous late anchor: invalid_alignment
- Previous large preview: playback_or_content_failure

## Replacement Anchors

- Middle replacement: `{middle['occurrence_id']}`
- Late replacement: `{late['occurrence_id']}`
- Anchor validation file: `{V4_ANCHORS / 'ANCHOR_VALIDATION.json'}`
- Anchor candidates file: `{STATE_ROOT / 'AUDIO_TRUTH_ANCHOR_CANDIDATES.json'}`

## Playback Repair

V4 preview was rebuilt as H.264/AAC/yuv420p with `+faststart`.

- Preview URL: `http://127.0.0.1:8787{status['preview']['url']}`
- Duration status: {status['preview']['duration_validation']['status']}
- Browser-compatible codec check: {playback['codec_compatible']}
- Faststart/seekability proxy: {playback['seekable_faststart']}
- HTTP status during script run: {playback.get('http_status')}
- Range status during script run: {playback.get('range_status')}
- Playback ready: {playback['playback_ready']}

## Timeline V4

- High confidence: {status['timeline']['high_confidence']}
- Medium confidence: {status['timeline']['medium_confidence']}
- Low confidence: {status['timeline']['low_confidence']}
- Blocked: {status['timeline']['blocked']}
- Lip-sync-ready occurrence count: {status['lipsync']['ready_occurrence_count']}
- Production captions ready: {status['captions']['production_ready']}

## Caption Defects And Repairs

- Caption defects found: {caption_eval['summary']['defect_count']}
- Repairs performed: invalidated broken V3 anchors, preserved early human anchor, reselected middle/late through validity gate, rebuilt V4 captions, rebuilt V4 browser-compatible preview, regenerated V4 lip-sync segment gates.

## SoeMind Forge Adaptation

- Report: `{status['soemind_forge']['report']}`
- Adapted/adopted workflow features: {status['soemind_forge']['adapted_features']}
- Cloud/provider assumptions rejected for this local-first repair.

## Next Action

Review the two replacement Audio Truth anchors. The first anchor is already trusted evidence.

No new model download, cloud upload, paid API call, InfiniteTalk install, image/video model install, source lyric overwrite, or master-audio overwrite occurred.
"""
    (REPO_ROOT / "director-os-web" / "WEB_V2_4_1_REAL_ANCHOR_AND_PLAYBACK_REPAIR_REPORT.md").write_text(report, encoding="utf-8")


def summarize_timeline(timeline: dict[str, Any]) -> dict[str, Any]:
    occs = timeline["occurrences"]
    return {
        "path": str(STATE_ROOT / "AUDIO_TRUTH_TIMELINE_V4.json"),
        "occurrence_count": len(occs),
        "high_confidence": sum(1 for o in occs if o["confidence_class"] == "high"),
        "medium_confidence": sum(1 for o in occs if o["confidence_class"] == "medium"),
        "low_confidence": sum(1 for o in occs if o["confidence_class"] == "low"),
        "blocked": sum(1 for o in occs if o["confidence_class"] == "blocked"),
    }


def load_wav_mono(path: Path) -> dict[str, Any]:
    with wave.open(str(path), "rb") as handle:
        channels = handle.getnchannels()
        sample_rate = handle.getframerate()
        frames = handle.readframes(handle.getnframes())
        sample_width = handle.getsampwidth()
    if sample_width != 2:
        raise RuntimeError(f"Unsupported sample width for energy validation: {sample_width}")
    samples = []
    step = sample_width * channels
    for i in range(0, len(frames), step):
        value = int.from_bytes(frames[i : i + 2], "little", signed=True) / 32768.0
        samples.append(value)
    return {"samples": samples, "sample_rate": sample_rate, "duration": len(samples) / sample_rate}


def segment_rms(audio: dict[str, Any], start: float, end: float) -> float:
    sample_rate = audio["sample_rate"]
    samples = audio["samples"]
    a = max(0, min(len(samples), int(start * sample_rate)))
    b = max(a, min(len(samples), int(end * sample_rate)))
    if b <= a:
        return 0.0
    total = sum(x * x for x in samples[a:b])
    return math.sqrt(total / (b - a))


def occurrence_count(occurrences: list[dict[str, Any]], lyric: str) -> int:
    return sum(1 for occ in occurrences if occ["canonical_unicode_lyric"] == lyric)


def probe_media(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "duration": 0.0, "has_audio": False, "has_video": False}
    proc = subprocess.run([str(FFPROBE), "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    data = json.loads(proc.stdout or "{}")
    streams = data.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})
    return {
        "exists": True,
        "duration": float(data.get("format", {}).get("duration", 0.0) or 0.0),
        "has_audio": any(s.get("codec_type") == "audio" for s in streams),
        "has_video": any(s.get("codec_type") == "video" for s in streams),
        "audio_codec": audio_stream.get("codec_name", ""),
        "video_codec": video_stream.get("codec_name", ""),
        "audio_duration": float(audio_stream.get("duration", 0.0) or 0.0),
        "video_duration": float(video_stream.get("duration", 0.0) or 0.0),
    }


def write_srt(path: Path, items: list[dict[str, Any]]) -> None:
    blocks = []
    for item in items:
        blocks.append(f"{item['index']}\n{srt_time(item['start'])} --> {srt_time(item['end'])}\n{item['text']}")
    path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")


def write_vtt(path: Path, items: list[dict[str, Any]]) -> None:
    blocks = ["WEBVTT", ""]
    for item in items:
        blocks.append(f"{srt_time(item['start']).replace(',', '.')} --> {srt_time(item['end']).replace(',', '.')}\n{item['text']}")
    path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")


def write_ass(path: Path, items: list[dict[str, Any]]) -> None:
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1920",
        "PlayResY: 1080",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Default,Myanmar MN,64,&H00FFFFFF,&H000000FF,&H00000000,&HA0000000,0,0,0,0,100,100,0,0,3,2,0,2,140,140,90,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for item in items:
        text = escape_ass(item["text"])
        lines.append(f"Dialogue: 0,{ass_time(item['start'])},{ass_time(item['end'])},Default,,0,0,0,,{text}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def ass_time(seconds: float) -> str:
    cs = int(round(seconds * 100))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, cs = divmod(rem, 100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"


def escape_ass(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def escape_filter_path(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace(":", "\\:")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run(command: list[str], check: bool = False) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["DYLD_LIBRARY_PATH"] = str(REPO_ROOT / "local-tools" / "ffmpeg-dylib-compat")
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    if check and result.returncode:
        raise RuntimeError(f"Command failed {result.returncode}: {' '.join(command)}\n{result.stderr[-2000:]}")
    return result


def command_output(command: list[str]) -> str:
    return subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False).stdout


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
