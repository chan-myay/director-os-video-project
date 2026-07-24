from __future__ import annotations

import json
import math
import shutil
import subprocess
import wave
from pathlib import Path
from typing import Any

from app.config import ENGINE_ROOT, REPO_ROOT
from app.services.db import connect, initialize_database
from app.services.director_workspace_service import list_storyboard_cards, raw_png, tc_duration
from app.services.lyric_timing_service import (
    FINAL_CAPTION_V2_ROOT,
    MASTER_AUDIO,
    conversion_review_summary,
    lipsync_readiness_summary,
    rebuild_caption_v2,
    validate_phrase_timing,
    voice_sync_summary,
)
from app.system_tools.ffmpeg_service import ffmpeg_path, ffprobe_path, probe_media


ANIMATIC_ROOT = ENGINE_ROOT / "animatics"
CAPTION_V3_ROOT = ENGINE_ROOT / "captions" / "final-timing-v3"
MUSIC_ANALYSIS_PATH = ENGINE_ROOT / "state" / "MUSIC_ANALYSIS.json"
AUDIT_PATH = REPO_ROOT / "director-os-web" / "ANIMATIC_SYNC_REALITY_AUDIT.md"


def animatic_reality_audit() -> dict[str, Any]:
    initialize_database()
    master = probe_media(MASTER_AUDIO)
    run11 = ANIMATIC_ROOT / "11"
    clean = _probe_optional(run11 / "ANIMATIC.mp4")
    captioned = _probe_optional(run11 / "ANIMATIC_WITH_CAPTIONS.mp4")
    review = _probe_optional(run11 / "ANIMATIC_REVIEW.mp4")
    command = _read_json(run11 / "FFMPEG_COMMAND.json")
    storyboard_duration = sum(tc_duration(card["timecode_start"], card["timecode_end"]) for card in list_storyboard_cards())
    phrases = _phrases()
    gaps = phrase_gaps(phrases, float(master["duration"]))
    used_shortest = "-shortest" in json.dumps(command)
    cutoff = bool(clean) and abs(float(master["duration"]) - float(clean.get("duration", 0))) > 1
    data = {
        "master_song_path": str(MASTER_AUDIO),
        "master_song_duration": master["duration"],
        "run11_clean_duration": clean.get("duration", 0),
        "run11_captioned_duration": captioned.get("duration", 0),
        "run11_review_duration": review.get("duration", 0),
        "audio_cut_off": cutoff,
        "used_shortest": used_shortest,
        "storyboard_timeline_duration": storyboard_duration,
        "storyboard_shorter_than_song": storyboard_duration + 1 < float(master["duration"]),
        "caption_timing_source": "phrase_boundary_local_analysis",
        "caption_font_used": _font_from_run_log(run11 / "BUILD_LOG.txt"),
        "burmese_font_readable": font_check()["readable"],
        "phrase_coverage_gaps": gaps,
        "instrumental_gaps": gaps,
        "ending_gap": max(0, float(master["duration"]) - (phrases[-1]["final_end_time"] if phrases else 0)),
        "run11_captioned_safe_for_review": False,
        "reason": "Run 11 used -shortest and is shorter than the master song; captions were not visibly marked as unverified.",
    }
    AUDIT_PATH.write_text(render_audit(data), encoding="utf-8")
    mark_run11_superseded()
    return data


def mark_run11_superseded() -> None:
    path = ANIMATIC_ROOT / "11" / "SUPERSEDED_STATUS.json"
    path.write_text(
        json.dumps(
            {
                "status": "superseded_review_defective",
                "reason": "Caption review animatic used truncated audio and unverified caption timing.",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def music_analysis() -> dict[str, Any]:
    initialize_database()
    wav = REPO_ROOT / "audio" / "01-analysis.wav"
    if not wav.exists():
        wav = _make_analysis_wav()
    energy = []
    duration = 0.0
    with wave.open(str(wav), "rb") as handle:
        rate = handle.getframerate()
        channels = handle.getnchannels()
        chunk = max(rate, 1)
        index = 0
        while True:
            frames = handle.readframes(chunk)
            if not frames:
                break
            samples = _pcm16_samples(frames, channels)
            if samples:
                rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples)) / 32768.0
                energy.append({"time": index, "rms": round(rms, 5)})
            index += 1
        duration = handle.getnframes() / float(rate or 1)
    phrases = _phrases()
    vocal_regions = [{"start": row["final_start_time"], "end": row["final_end_time"], "phrase_id": row["phrase_id"]} for row in phrases]
    instrumental = phrase_gaps(phrases, duration)
    peaks = sorted(energy, key=lambda item: item["rms"], reverse=True)[:12]
    data = {
        "master_audio": str(MASTER_AUDIO),
        "analysis_wav": str(wav),
        "duration": duration,
        "energy_curve": energy,
        "vocal_phrase_regions": vocal_regions,
        "instrumental_regions": instrumental,
        "intro": instrumental[0] if instrumental else None,
        "outro": instrumental[-1] if instrumental else None,
        "energy_peaks": sorted(peaks, key=lambda item: item["time"]),
        "caption_regions": vocal_regions,
        "warning": "Lyric timing is boundary-based, not word/phoneme alignment or verified lyric recognition.",
    }
    MUSIC_ANALYSIS_PATH.parent.mkdir(parents=True, exist_ok=True)
    MUSIC_ANALYSIS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return data


def font_check() -> dict[str, Any]:
    candidates = [
        ("Noto Sans Myanmar", Path("/System/Library/Fonts/NotoSansMyanmar.ttc")),
        ("Myanmar MN", Path("/System/Library/Fonts/Supplemental/Myanmar MN.ttc")),
        ("Myanmar Sangam MN", Path("/System/Library/Fonts/Supplemental/Myanmar Sangam MN.ttc")),
        ("Padauk", Path("/Library/Fonts/Padauk.ttf")),
    ]
    detected = [{"name": name, "path": str(path), "exists": path.exists()} for name, path in candidates]
    selected = next((item for item in detected if item["exists"]), None)
    status = {
        "detected_fonts": detected,
        "selected_font": selected["name"] if selected else "",
        "selected_font_path": selected["path"] if selected else "",
        "readable": bool(selected),
        "warnings": [] if selected else ["NO_BURMESE_FONT_DETECTED"],
        "ass_style": "Fontsize 58, outline 3, shadow 1, safe bottom margin 88, high contrast",
        "sample_text": "အချစ်မဲ့ ဇာတ်လမ်း",
    }
    (CAPTION_V3_ROOT / "CAPTION_FONT_STATUS.json").parent.mkdir(parents=True, exist_ok=True)
    (CAPTION_V3_ROOT / "CAPTION_FONT_STATUS.json").write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return status


def caption_v3_exports() -> dict[str, Any]:
    initialize_database()
    CAPTION_V3_ROOT.mkdir(parents=True, exist_ok=True)
    font = font_check()
    phrases = _phrases()
    sync = listening_sync_status()
    blockers = []
    if not font["readable"]:
        blockers.append("READABLE_BURMESE_FONT_MISSING")
    for phrase in phrases:
        if phrase["display_status"] != "approved_unicode" or not phrase["approved_display_text"]:
            blockers.append(f"PHRASE_{phrase['phrase_id']}_APPROVED_UNICODE_MISSING")
        if phrase["listening_sync_status"] not in {"correct_line_verified"}:
            blockers.append(f"PHRASE_{phrase['phrase_id']}_LISTENING_SYNC_UNVERIFIED")
    review_rows = [_review_caption_row(row) for row in phrases]
    (CAPTION_V3_ROOT / "CAPTIONS_REVIEW.srt").write_text(_render_srt(review_rows), encoding="utf-8")
    (CAPTION_V3_ROOT / "CAPTIONS_REVIEW.vtt").write_text(_render_vtt(review_rows), encoding="utf-8")
    (CAPTION_V3_ROOT / "CAPTIONS_REVIEW.ass").write_text(_render_ass(review_rows, font, review=True), encoding="utf-8")
    production_written = False
    if not blockers:
        production_rows = [_production_caption_row(row) for row in phrases]
        (CAPTION_V3_ROOT / "CAPTIONS_PRODUCTION.srt").write_text(_render_srt(production_rows), encoding="utf-8")
        (CAPTION_V3_ROOT / "CAPTIONS_PRODUCTION.vtt").write_text(_render_vtt(production_rows), encoding="utf-8")
        (CAPTION_V3_ROOT / "CAPTIONS_PRODUCTION.ass").write_text(_render_ass(production_rows, font, review=False), encoding="utf-8")
        production_written = True
    status = {
        "review_captions_available": True,
        "production_captions_ready": production_written,
        "timing_source": "phrase_boundary_local_analysis",
        "verified_phrases": sync["verified_phrases"],
        "unverified_phrases": sync["unverified_phrases"],
        "wrong_line_phrases": sync["wrong_line_phrases"],
    }
    (CAPTION_V3_ROOT / "CAPTION_SYNC_STATUS.json").write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (CAPTION_V3_ROOT / "CAPTION_BLOCKERS.json").write_text(json.dumps({"blockers": blockers}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"root": str(CAPTION_V3_ROOT), "font": font, "sync": status, "blockers": blockers}


def build_full_song_review_animatic() -> dict[str, Any]:
    initialize_database()
    audit = animatic_reality_audit()
    captions = caption_v3_exports()
    version = next_animatic_version()
    run_dir = ANIMATIC_ROOT / str(version)
    run_dir.mkdir(parents=True, exist_ok=False)
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
    commands: dict[str, list[str]] = {}
    base = [
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
    commands["clean"] = [ffmpeg_path(), *base]
    _run_ffmpeg(base, log)
    vf_caption = f"subtitles={_escape_filter_path(CAPTION_V3_ROOT / 'CAPTIONS_REVIEW.ass')}"
    cap = ["-y", "-i", str(clean), "-vf", vf_caption, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "copy", str(captioned)]
    commands["captioned_review"] = [ffmpeg_path(), *cap]
    _run_ffmpeg(cap, log)
    overlay = "drawtext=text='UNVERIFIED LYRIC TIMING - REVIEW ONLY':x=40:y=40:fontsize=42:fontcolor=white:box=1:boxcolor=black@0.65"
    rev = ["-y", "-i", str(clean), "-vf", overlay, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "copy", str(review)]
    commands["review"] = [ffmpeg_path(), *rev]
    _run_ffmpeg(rev, log)
    metadata = {name: _probe_optional(path) for name, path in {"clean": clean, "captioned_review": captioned, "review": review}.items()}
    validation = duration_validation(master_duration, metadata.get("clean", {}).get("duration", 0))
    (run_dir / "FFMPEG_COMMAND.json").write_text(json.dumps(commands, indent=2) + "\n", encoding="utf-8")
    (run_dir / "MEDIA_METADATA.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    (run_dir / "DURATION_VALIDATION.json").write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")
    (run_dir / "CAPTION_SYNC_STATUS.json").write_text(json.dumps(captions["sync"], indent=2) + "\n", encoding="utf-8")
    (run_dir / "FONT_STATUS.json").write_text(json.dumps(captions["font"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"version": version, "run_dir": str(run_dir), "metadata": metadata, "duration_validation": validation, "audit": audit}


def latest_safe_animatic_context() -> dict[str, Any]:
    candidates = sorted([p for p in ANIMATIC_ROOT.iterdir() if p.is_dir() and (p / "DURATION_VALIDATION.json").exists()], key=lambda p: int(p.name) if p.name.isdigit() else -1)
    latest = candidates[-1] if candidates else ANIMATIC_ROOT / "11"
    validation = _read_json(latest / "DURATION_VALIDATION.json")
    return {
        "latest_version": latest.name,
        "latest_path": str(latest),
        "validation": validation,
        "font": _read_json(latest / "FONT_STATUS.json") or font_check(),
        "sync": _read_json(latest / "CAPTION_SYNC_STATUS.json") or listening_sync_status(),
        "blockers": (json.loads((CAPTION_V3_ROOT / "CAPTION_BLOCKERS.json").read_text(encoding="utf-8")).get("blockers", []) if (CAPTION_V3_ROOT / "CAPTION_BLOCKERS.json").exists() else []),
    }


def listening_sync_status() -> dict[str, Any]:
    initialize_database()
    phrases = _phrases()
    for phrase in phrases:
        phrase["audio_segment"] = ensure_listening_segment(phrase)
    verified = sum(1 for p in phrases if p["listening_sync_status"] == "correct_line_verified")
    wrong = sum(1 for p in phrases if p["listening_sync_status"] == "wrong_line")
    return {
        "status": "auto_boundary_unverified" if verified < len(phrases) else "human_listening_verified",
        "phrases": phrases,
        "verified_phrases": verified,
        "unverified_phrases": len(phrases) - verified,
        "wrong_line_phrases": wrong,
        "review_url": "/burmese-language/listening-sync",
    }


def ensure_listening_segment(phrase: dict[str, Any]) -> str:
    root = ENGINE_ROOT / "listening-sync" / "phrases" / str(phrase["phrase_id"])
    root.mkdir(parents=True, exist_ok=True)
    out = root / "FULL_MIX_SEGMENT.wav"
    if out.exists():
        return str(out.relative_to(ENGINE_ROOT))
    start = max(0.0, float(phrase["final_start_time"]) - 0.5)
    end = float(phrase["final_end_time"]) + 0.5
    duration = max(end - start, 0.25)
    subprocess.run(
        [ffmpeg_path(), "-y", "-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-i", str(MASTER_AUDIO), "-ar", "44100", "-ac", "1", str(out)],
        capture_output=True,
        text=True,
        check=False,
    )
    return str(out.relative_to(ENGINE_ROOT))


def update_listening_sync(phrase_id: int, status: str, notes: str = "") -> tuple[bool, str]:
    allowed = {"correct_line_verified", "wrong_line", "timing_too_early", "timing_too_late", "too_short", "too_long", "needs_split", "needs_merge", "instrumental", "uncertain"}
    if status not in allowed:
        return False, "Invalid listening sync status."
    with connect() as conn:
        conn.execute(
            "UPDATE lyric_phrases SET listening_sync_status = ?, listening_sync_notes = ? WHERE phrase_id = ?",
            (status, notes, phrase_id),
        )
    caption_v3_exports()
    return True, "Listening sync review saved."


def caption_readiness() -> dict[str, Any]:
    caps = caption_v3_exports()
    voice = voice_sync_summary()
    return {
        "production_captions_ready": not caps["blockers"],
        "review_captions_available": True,
        "blockers": caps["blockers"],
        "font_readable": caps["font"]["readable"],
        "voice_sync_status": "not_tested_no_voice_audio" if voice["measured_voice_count"] == 0 else "voice_audio_measured_review_required",
    }


def duration_validation(master_duration: float, animatic_duration: float) -> dict[str, Any]:
    diff = abs(float(master_duration) - float(animatic_duration))
    if diff <= 0.5:
        status = "ok"
    elif diff <= 1.0:
        status = "warning"
    else:
        status = "hard_failure"
    return {"master_duration": master_duration, "animatic_duration": animatic_duration, "difference": diff, "status": status, "mode": "full_song"}


def next_animatic_version() -> int:
    nums = [int(path.name) for path in ANIMATIC_ROOT.iterdir() if path.is_dir() and path.name.isdigit()]
    return max(nums or [11]) + 1


def frame_entries_for_full_song(cards: list[dict[str, Any]], master_duration: float, run_dir: Path) -> list[tuple[str, float]]:
    entries: list[tuple[str, float]] = []
    total = 0.0
    for card in cards:
        duration = max(tc_duration(card["timecode_start"], card["timecode_end"]), 2)
        entries.append((str(Path(card["raster_path"]).resolve()), duration))
        total += duration
    if total < master_duration:
        filler = run_dir / "FULL_SONG_FILLER.png"
        write_filler_png(filler)
        entries.append((str(filler.resolve()), master_duration - total))
    return entries


def write_filler_png(path: Path) -> None:
    width, height = 1280, 720
    pixels = bytearray()
    for y in range(height):
        row = bytearray()
        for x in range(width):
            r = 10 + int(18 * y / height)
            g = 12 + int(10 * x / width)
            b = 16 + int(35 * (1 - y / height))
            if 850 < x < 1120 and 80 < y < 360:
                b = min(180, b + 50)
            if 120 < x < 420 and 500 < y < 610:
                r, g, b = 96, 42, 38
            row.extend((r, g, b))
        pixels.extend(b"\x00" + row)
    raw_png(path, width, height, bytes(pixels))


def phrase_gaps(phrases: list[dict[str, Any]], duration: float) -> list[dict[str, float]]:
    gaps = []
    cursor = 0.0
    for row in phrases:
        start = float(row["final_start_time"])
        end = float(row["final_end_time"])
        if start - cursor > 0.25:
            gaps.append({"start": round(cursor, 3), "end": round(start, 3), "duration": round(start - cursor, 3)})
        cursor = max(cursor, end)
    if duration - cursor > 0.25:
        gaps.append({"start": round(cursor, 3), "end": round(duration, 3), "duration": round(duration - cursor, 3)})
    return gaps


def _phrases() -> list[dict[str, Any]]:
    initialize_database()
    with connect() as conn:
        rows = conn.execute("SELECT * FROM lyric_phrases ORDER BY phrase_index").fetchall()
    return [dict(row) for row in rows]


def _run_ffmpeg(args: list[str], log: Path) -> None:
    result = subprocess.run([ffmpeg_path(), *args], capture_output=True, text=True, check=False)
    with log.open("a", encoding="utf-8") as handle:
        handle.write("$ " + " ".join([ffmpeg_path(), *args]) + "\n")
        handle.write(result.stdout)
        handle.write(result.stderr)
        handle.write("\n")


def _render_srt(rows: list[dict[str, Any]]) -> str:
    return "\n".join(f"{i}\n{_srt(row['final_start_time'])} --> {_srt(row['final_end_time'])}\n{row['caption_text']}\n" for i, row in enumerate(rows, start=1))


def _render_vtt(rows: list[dict[str, Any]]) -> str:
    return "WEBVTT\n\n" + "\n".join(f"{_vtt(row['final_start_time'])} --> {_vtt(row['final_end_time'])}\n{row['caption_text']}\n" for row in rows)


def _render_ass(rows: list[dict[str, Any]], font: dict[str, Any], review: bool) -> str:
    font_name = font.get("selected_font") or "Arial"
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Burmese,{font_name},58,&H00FFFFFF,&H000000FF,&H00000000,&HAA000000,0,0,0,0,100,100,0,0,3,3,1,2,80,80,88,1
Style: Warning,{font_name},42,&H0000FFFF,&H000000FF,&H00000000,&HAA000000,1,0,0,0,100,100,0,0,3,2,1,8,60,60,46,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    if review:
        end = rows[-1]["final_end_time"] if rows else 10
        events.append(f"Dialogue: 1,0:00:00.00,{_ass(end)},Warning,,0,0,0,,UNVERIFIED LYRIC TIMING")
    for row in rows:
        events.append(f"Dialogue: 0,{_ass(row['final_start_time'])},{_ass(row['final_end_time'])},Burmese,,0,0,0,,{row['caption_text']}")
    return header + "\n".join(events) + "\n"


def _review_caption_row(row: dict[str, Any]) -> dict[str, Any]:
    text = row.get("approved_display_text") or row.get("normalized_unicode") or row.get("original_text") or ""
    copy = dict(row)
    copy["caption_text"] = f"P{row['phrase_index']} UNVERIFIED: {text}"
    return copy


def _production_caption_row(row: dict[str, Any]) -> dict[str, Any]:
    copy = dict(row)
    copy["caption_text"] = row["approved_display_text"]
    return copy


def _srt(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _vtt(seconds: float) -> str:
    return _srt(seconds).replace(",", ".")


def _ass(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _probe_optional(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return probe_media(path)
    except Exception as exc:
        return {"error": str(exc)}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _font_from_run_log(path: Path) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="ignore")
    for line in text.splitlines():
        if "fontselect" in line:
            return line
    return ""


def _escape_filter_path(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def _make_analysis_wav() -> Path:
    out = REPO_ROOT / "audio" / "01-analysis.wav"
    subprocess.run([ffmpeg_path(), "-y", "-i", str(MASTER_AUDIO), "-ar", "16000", "-ac", "1", str(out)], check=False, capture_output=True, text=True)
    return out


def _pcm16_samples(frames: bytes, channels: int) -> list[int]:
    if len(frames) < 2:
        return []
    count = len(frames) // 2
    samples = [int.from_bytes(frames[i * 2 : i * 2 + 2], "little", signed=True) for i in range(count)]
    if channels > 1:
        samples = samples[::channels]
    return samples


def render_audit(data: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Animatic Sync Reality Audit",
            "",
            f"Master song: `{data['master_song_path']}`",
            f"Master duration: {data['master_song_duration']}",
            f"Run 11 clean duration: {data['run11_clean_duration']}",
            f"Run 11 captioned duration: {data['run11_captioned_duration']}",
            f"Run 11 review duration: {data['run11_review_duration']}",
            f"Audio cut off: {data['audio_cut_off']}",
            f"Used -shortest: {data['used_shortest']}",
            f"Storyboard shorter than song: {data['storyboard_shorter_than_song']}",
            f"Caption timing source: {data['caption_timing_source']}",
            f"Caption font used: {data['caption_font_used']}",
            f"Burmese font readable: {data['burmese_font_readable']}",
            f"Ending gap: {data['ending_gap']}",
            f"Run 11 captioned safe for review: {data['run11_captioned_safe_for_review']}",
            "",
            data["reason"],
            "",
        ]
    )
