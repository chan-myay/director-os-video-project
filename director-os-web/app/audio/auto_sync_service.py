from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from app.audio.local_asr_service import local_asr_status
from app.audio.lyric_audio_matcher import match_phrases_to_boundaries
from app.config import ENGINE_ROOT
from app.services.director_workspace_service import list_storyboard_cards, raw_png, tc_duration
from app.services.lyric_timing_service import MASTER_AUDIO, lipsync_readiness_summary, voice_sync_summary
from app.services.v104_animatic_sync_service import (
    _ass,
    _escape_filter_path,
    _probe_optional,
    _run_ffmpeg,
    _srt,
    _vtt,
    duration_validation,
    font_check,
    frame_entries_for_full_song,
    music_analysis,
    phrase_gaps,
)
from app.services.v104_animatic_sync_service import _phrases as lyric_phrases
from app.system_tools.ffmpeg_service import ffmpeg_path, probe_media


AUTO_SYNC_PATH = ENGINE_ROOT / "state" / "AUTO_LYRIC_SYNC.json"
CAPTION_V4_ROOT = ENGINE_ROOT / "captions" / "final-timing-v4"
FONT_PREVIEW_ROOT = ENGINE_ROOT / "captions" / "font-preview"
ANIMATIC_ROOT = ENGINE_ROOT / "animatics"


def auto_sync_lyrics() -> dict[str, Any]:
    analysis = music_analysis()
    phrases = lyric_phrases()
    gaps = analysis.get("instrumental_regions") or phrase_gaps(phrases, float(analysis.get("duration") or 0))
    matches = match_phrases_to_boundaries(phrases, gaps)
    low_confidence = [item for item in matches if item["confidence"] < 0.7]
    blocked = [item for item in matches if item["likely_wrong_line"] or not item["caption_safe"]]
    data = {
        "sync_version": "v1.0.5",
        "master_audio": str(MASTER_AUDIO),
        "master_duration": analysis.get("duration"),
        "method": "level_b_existing_vocal_boundary_plus_phrase_order",
        "asr": local_asr_status(),
        "status": "auto_boundary_unverified",
        "phrase_count": len(matches),
        "auto_synced_phrase_count": len(matches),
        "low_confidence_phrase_count": len(low_confidence),
        "blocked_phrase_count": len(blocked),
        "instrumental_regions": gaps,
        "phrases": matches,
        "warning": "This is automatic boundary/order sync, not word, syllable, phoneme, or ASR-verified lyric recognition.",
    }
    AUTO_SYNC_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUTO_SYNC_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return data


def auto_sync_status() -> dict[str, Any]:
    if not AUTO_SYNC_PATH.exists():
        return auto_sync_lyrics()
    try:
        return json.loads(AUTO_SYNC_PATH.read_text(encoding="utf-8"))
    except Exception:
        return auto_sync_lyrics()


def font_render_preview() -> dict[str, Any]:
    font = font_check()
    FONT_PREVIEW_ROOT.mkdir(parents=True, exist_ok=True)
    sample = FONT_PREVIEW_ROOT / "FONT_SAMPLE.png"
    overlay = FONT_PREVIEW_ROOT / "CAPTION_OVERLAY_SAMPLE.png"
    status_path = FONT_PREVIEW_ROOT / "FONT_RENDER_STATUS.json"
    text = font.get("sample_text") or "အချစ်မဲ့ ဇာတ်လမ်း"
    fontfile = font.get("selected_font_path") or ""
    errors: list[str] = []
    if not fontfile:
        errors.append("NO_BURMESE_FONT_DETECTED")
    else:
        draw = f"drawtext=fontfile='{_escape_filter_path(Path(fontfile))}':text='{text}':fontsize=72:fontcolor=white:borderw=4:bordercolor=black:x=(w-text_w)/2:y=(h-text_h)/2"
        cmd = [
            ffmpeg_path(),
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=0x101014:s=1280x720:d=1",
            "-frames:v",
            "1",
            "-vf",
            draw,
            str(sample),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0 or not sample.exists():
            errors.append("FONT_RENDER_FAILED")
        draw_overlay = f"drawtext=fontfile='{_escape_filter_path(Path(fontfile))}':text='UNVERIFIED LYRIC TIMING  P01  {text}':fontsize=54:fontcolor=white:borderw=4:bordercolor=black:box=1:boxcolor=black@0.55:x=80:y=h-170"
        result2 = subprocess.run(
            [
                ffmpeg_path(),
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=0x1b1212:s=1920x1080:d=1",
                "-frames:v",
                "1",
                "-vf",
                draw_overlay,
                str(overlay),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result2.returncode != 0 or not overlay.exists():
            errors.append("CAPTION_OVERLAY_RENDER_FAILED")
    data = {
        **font,
        "font_sample": str(sample) if sample.exists() else "",
        "caption_overlay_sample": str(overlay) if overlay.exists() else "",
        "render_test_passed": not errors,
        "errors": errors,
        "tofu_detection": "not_available_without_image_glyph_classifier",
        "size_check": "1080p caption preview uses fontsize 54-72 with outline/box",
    }
    status_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return data


def rebuild_caption_v4() -> dict[str, Any]:
    sync = auto_sync_lyrics()
    font = font_render_preview()
    CAPTION_V4_ROOT.mkdir(parents=True, exist_ok=True)
    rows = [_caption_row(item) for item in sync["phrases"] if item["caption_safe"]]
    (CAPTION_V4_ROOT / "CAPTIONS_REVIEW_AUTO.srt").write_text(_render_srt(rows), encoding="utf-8")
    (CAPTION_V4_ROOT / "CAPTIONS_REVIEW_AUTO.vtt").write_text(_render_vtt(rows), encoding="utf-8")
    (CAPTION_V4_ROOT / "CAPTIONS_REVIEW_AUTO.ass").write_text(_render_ass(rows, font), encoding="utf-8")
    blockers = []
    if not font.get("render_test_passed"):
        blockers.append("FONT_RENDER_PREVIEW_FAILED")
    blockers.extend([f"PHRASE_{item['phrase_id']}_AUTO_SYNC_LOW_CONFIDENCE" for item in sync["phrases"] if item["confidence"] < 0.7])
    blockers.extend([f"PHRASE_{item['phrase_id']}_LISTENING_SYNC_UNVERIFIED" for item in sync["phrases"] if item["needs_human_review"]])
    blockers.append("APPROVED_UNICODE_REVIEW_REQUIRED")
    (CAPTION_V4_ROOT / "AUTO_SYNC_STATUS.json").write_text(json.dumps(sync, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (CAPTION_V4_ROOT / "CAPTION_BLOCKERS.json").write_text(json.dumps({"blockers": blockers}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (CAPTION_V4_ROOT / "FONT_STATUS.json").write_text(json.dumps(font, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"root": str(CAPTION_V4_ROOT), "sync": sync, "font": font, "blockers": blockers, "review_caption_count": len(rows)}


def build_animatic_v13() -> dict[str, Any]:
    captions = rebuild_caption_v4()
    version = 13
    run_dir = ANIMATIC_ROOT / str(version)
    run_dir.mkdir(parents=True, exist_ok=True)
    cards = list_storyboard_cards()
    master_duration = float(probe_media(MASTER_AUDIO)["duration"])
    frame_entries = frame_entries_for_full_song(cards, master_duration, run_dir)
    frames_txt = run_dir / "frames.txt"
    with frames_txt.open("w", encoding="utf-8") as handle:
        for image, duration in frame_entries:
            handle.write(f"file '{image}'\n")
            handle.write(f"duration {duration:.3f}\n")
        if frame_entries:
            handle.write(f"file '{frame_entries[-1][0]}'\n")
    clean = run_dir / "ANIMATIC.mp4"
    captioned = run_dir / "ANIMATIC_WITH_CAPTIONS_REVIEW.mp4"
    review = run_dir / "ANIMATIC_REVIEW.mp4"
    log = run_dir / "BUILD_LOG.txt"
    if log.exists():
        log.unlink()
    commands: dict[str, list[str]] = {}
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
        cap_args = [
            "-y",
            "-i",
            str(clean),
            "-vf",
            f"subtitles={_escape_filter_path(CAPTION_V4_ROOT / 'CAPTIONS_REVIEW_AUTO.ass')}",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-c:a",
            "copy",
            str(captioned),
        ]
        commands["captioned_review"] = [ffmpeg_path(), *cap_args]
        _run_ffmpeg(cap_args, log)
    review_args = [
        "-y",
        "-i",
        str(clean),
        "-vf",
        "drawtext=text='REVIEW ONLY - AUTO LYRIC SYNC UNVERIFIED':x=40:y=40:fontsize=42:fontcolor=white:box=1:boxcolor=black@0.65",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-c:a",
        "copy",
        str(review),
    ]
    commands["review"] = [ffmpeg_path(), *review_args]
    _run_ffmpeg(review_args, log)
    metadata = {name: _probe_optional(path) for name, path in {"clean": clean, "captioned_review": captioned, "review": review}.items()}
    validation = duration_validation(master_duration, metadata.get("clean", {}).get("duration", 0))
    (run_dir / "DURATION_VALIDATION.json").write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")
    (run_dir / "AUTO_SYNC_STATUS.json").write_text(json.dumps(captions["sync"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (run_dir / "FONT_STATUS.json").write_text(json.dumps(captions["font"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (run_dir / "FFMPEG_COMMAND.json").write_text(json.dumps(commands, indent=2) + "\n", encoding="utf-8")
    (run_dir / "MEDIA_METADATA.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return {"version": version, "run_dir": str(run_dir), "metadata": metadata, "duration_validation": validation, "captions": captions}


def v105_caption_readiness() -> dict[str, Any]:
    caps = rebuild_caption_v4()
    voice = voice_sync_summary()
    return {
        "production_captions_ready": False,
        "review_captions_available": True,
        "auto_synced_phrase_count": caps["sync"]["auto_synced_phrase_count"],
        "low_confidence_phrase_count": caps["sync"]["low_confidence_phrase_count"],
        "blocked_phrase_count": caps["sync"]["blocked_phrase_count"],
        "blockers": caps["blockers"],
        "font_readable": caps["font"].get("readable", False),
        "font_render_test_passed": caps["font"].get("render_test_passed", False),
        "voice_sync_status": voice.get("status", "not_tested_no_voice_audio"),
    }


def v105_lipsync_readiness() -> dict[str, Any]:
    base = lipsync_readiness_summary()
    sync = auto_sync_status()
    reasons = []
    if sync.get("low_confidence_phrase_count", 0):
        reasons.append("blocked_on_auto_sync_low_confidence")
    if base.get("blocked_phrase_count", 0):
        reasons.append("blocked_on_listening_review")
    reasons.append("blocked_on_unicode_review")
    return {**base, "readiness_reasons": sorted(set(reasons)), "readiness_status": "blocked_on_auto_sync_low_confidence"}


def _caption_row(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "start": item["candidate_start"],
        "end": item["candidate_end"],
        "caption_text": f"P{item['phrase_index']} {item['review_label']} {item['confidence']:.2f}: {item['lyric_line']}",
    }


def _render_srt(rows: list[dict[str, Any]]) -> str:
    return "\n".join(f"{i}\n{_srt(row['start'])} --> {_srt(row['end'])}\n{row['caption_text']}\n" for i, row in enumerate(rows, start=1))


def _render_vtt(rows: list[dict[str, Any]]) -> str:
    return "WEBVTT\n\n" + "\n".join(f"{_vtt(row['start'])} --> {_vtt(row['end'])}\n{row['caption_text']}\n" for row in rows)


def _render_ass(rows: list[dict[str, Any]], font: dict[str, Any]) -> str:
    font_name = font.get("selected_font") or "Arial"
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Burmese,{font_name},54,&H00FFFFFF,&H000000FF,&H00000000,&HAA000000,0,0,0,0,100,100,0,0,3,4,1,2,80,80,92,1
Style: Warning,{font_name},42,&H0000FFFF,&H000000FF,&H00000000,&HAA000000,1,0,0,0,100,100,0,0,3,2,1,8,60,60,48,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    end = rows[-1]["end"] if rows else 10
    events = [f"Dialogue: 1,0:00:00.00,{_ass(end)},Warning,,0,0,0,,UNVERIFIED LYRIC TIMING - AUTO SYNC REVIEW"]
    for row in rows:
        events.append(f"Dialogue: 0,{_ass(row['start'])},{_ass(row['end'])},Burmese,,0,0,0,,{row['caption_text']}")
    return header + "\n".join(events) + "\n"
