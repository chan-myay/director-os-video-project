from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import wave
from pathlib import Path
from typing import Any

from app.burmese.caption_service import caption_safe_lines
from app.burmese.encoding_detector import detect_encoding
from app.burmese.normalization_service import normalize_burmese
from app.burmese.pronunciation_service import pronunciation_helper
from app.burmese.syllable_segmenter import segment_syllables
from app.burmese.zawgyi_unicode_service import zawgyi_to_unicode
from app.config import ENGINE_ROOT, REPO_ROOT
from app.services.audit_service import write_audit
from app.services.db import connect, initialize_database
from app.system_tools.ffmpeg_service import ffmpeg_path, ffprobe_path


LYRIC_TIMING_ROOT = ENGINE_ROOT / "burmese-language" / "timing-authority"
FINAL_CAPTION_ROOT = ENGINE_ROOT / "captions" / "final-timing"
FINAL_CAPTION_V2_ROOT = ENGINE_ROOT / "captions" / "final-timing-v2"
VOCAL_BOUNDARY_PATH = REPO_ROOT / "output" / "lyric-alignment" / "vocal-phrase-boundaries.json"
MASTER_AUDIO = REPO_ROOT / "audio" / "01.mp3"
VOICE_IMPORT_ROOT = ENGINE_ROOT / "voice-imports"


def build_lyric_timing_authority() -> dict[str, Any]:
    initialize_database()
    source = _find_lyric_source()
    raw_lines = source.read_text(encoding="utf-8", errors="strict").splitlines()
    boundary_data = _read_vocal_boundaries()
    vocal_phrases = boundary_data.get("phrases", [])
    audio_duration = _probe_audio_duration(MASTER_AUDIO)
    line_records = _record_source_lines(source, raw_lines)
    first_section_index = next((row["line_index"] for row in line_records if row["is_section_label"]), 0)
    lyric_lines = [
        row
        for row in line_records
        if row["original_text"].strip()
        and not row["is_section_label"]
        and (not first_section_index or row["line_index"] > first_section_index)
    ]
    phrase_rows = _record_phrase_timing(lyric_lines, vocal_phrases, boundary_data, audio_duration)
    exports = rebuild_caption_v2()
    summary = {
        "source_path": str(source.relative_to(REPO_ROOT)),
        "line_count": len(raw_lines),
        "lyric_phrase_count": len(phrase_rows),
        "vocal_boundary_count": len(vocal_phrases),
        "audio_duration": audio_duration,
        "timing_source": "phrase_boundary_local_analysis" if vocal_phrases else "duration_proportional_fallback",
        "word_level_asr": False,
        "conversion_note": "Confirmed Zawgyi lines are routed through ICU/PyICU when available, otherwise through the local rule converter. Pass-through is an explicit failure/review state.",
        "caption_v2_exports": exports,
    }
    LYRIC_TIMING_ROOT.mkdir(parents=True, exist_ok=True)
    (LYRIC_TIMING_ROOT / "LYRIC_TIMING_AUTHORITY.json").write_text(
        json.dumps({"summary": summary, "source_lines": line_records, "phrases": phrase_rows}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (LYRIC_TIMING_ROOT / "LYRIC_TIMING_AUTHORITY.md").write_text(_render_authority_md(summary, phrase_rows), encoding="utf-8")
    write_audit(
        "lyric_timing_authority_built",
        "lyric_phrases",
        "latest",
        "Lyric timing authority rebuilt from original lyric file and local vocal boundaries.",
        summary,
    )
    return {"summary": summary, "source_lines": line_records, "phrases": phrase_rows}


def lyric_timing_summary() -> dict[str, Any]:
    initialize_database()
    with connect() as conn:
        source_count = conn.execute("SELECT COUNT(*) FROM lyric_source_lines").fetchone()[0]
        phrase_count = conn.execute("SELECT COUNT(*) FROM lyric_phrases").fetchone()[0]
        locked_count = conn.execute("SELECT COUNT(*) FROM lyric_phrases WHERE lipsync_timing_locked = 1").fetchone()[0]
        rows = conn.execute(
            """
            SELECT p.*, l.detected_encoding, l.conversion_action, l.conversion_uncertain
            FROM lyric_phrases p
            JOIN lyric_source_lines l ON l.source_line_id = p.source_line_id
            ORDER BY p.phrase_index
            LIMIT 100
            """
        ).fetchall()
    return {
        "source_line_count": source_count,
        "phrase_count": phrase_count,
        "locked_count": locked_count,
        "records": [dict(row) for row in rows],
        "authority_path": str(LYRIC_TIMING_ROOT / "LYRIC_TIMING_AUTHORITY.json"),
        "caption_root": str(FINAL_CAPTION_ROOT),
    }


def phrase_for_shot_time(start: float, end: float) -> dict[str, Any] | None:
    initialize_database()
    midpoint = (start + end) / 2
    with connect() as conn:
        row = conn.execute(
            """
            SELECT p.*, l.original_text AS line_original_text
            FROM lyric_phrases p
            JOIN lyric_source_lines l ON l.source_line_id = p.source_line_id
            WHERE p.final_start_time <= ? AND p.final_end_time >= ?
            ORDER BY ABS(((p.final_start_time + p.final_end_time) / 2.0) - ?)
            LIMIT 1
            """,
            (end, start, midpoint),
        ).fetchone()
        if not row:
            row = conn.execute(
                """
                SELECT p.*, l.original_text AS line_original_text
                FROM lyric_phrases p
                JOIN lyric_source_lines l ON l.source_line_id = p.source_line_id
                ORDER BY ABS(((p.final_start_time + p.final_end_time) / 2.0) - ?)
                LIMIT 1
                """,
                (midpoint,),
            ).fetchone()
    return dict(row) if row else None


def voice_duration(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(str(path))
    duration = 0.0
    sample_rate = 0
    channels = 0
    if path.suffix.lower() == ".wav":
        with wave.open(str(path), "rb") as handle:
            sample_rate = handle.getframerate()
            channels = handle.getnchannels()
            duration = handle.getnframes() / float(sample_rate or 1)
    else:
        result = subprocess.run(
            [ffprobe_path(), "-v", "error", "-show_format", "-show_streams", "-print_format", "json", str(path)],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        data = json.loads(result.stdout)
        audio = next((stream for stream in data.get("streams", []) if stream.get("codec_type") == "audio"), {})
        duration = float(data.get("format", {}).get("duration") or 0)
        sample_rate = int(audio.get("sample_rate") or 0)
        channels = int(audio.get("channels") or 0)
    return {
        "path": str(path),
        "duration": duration,
        "sample_rate": sample_rate,
        "channels": channels,
        "sha256": _sha256(path),
    }


def import_voice_audio_for_phrase(phrase_id: int, source_path: str, provider: str = "manual_import") -> tuple[bool, str, dict[str, Any]]:
    initialize_database()
    path = Path(source_path).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / source_path
    with connect() as conn:
        phrase = conn.execute("SELECT * FROM lyric_phrases WHERE phrase_id = ?", (phrase_id,)).fetchone()
    if not phrase:
        return False, "Unknown lyric phrase.", {}
    if not path.exists() or path.suffix.lower() not in {".wav", ".mp3", ".m4a", ".aac"}:
        return False, "Unsupported or missing voice audio file.", {}
    managed = _managed_voice_copy(path, phrase_id)
    measured = voice_duration(managed)
    silence = estimate_silence(managed)
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO voice_audio_assets
                (phrase_id, source_path, provider, duration, sample_rate, channels, sha256, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'imported_measured')
            """,
            (
                phrase_id,
                str(managed),
                provider,
                measured["duration"],
                measured["sample_rate"],
                measured["channels"],
                measured["sha256"],
            ),
        )
        voice_asset_id = int(cursor.lastrowid)
        conn.execute(
            """
            INSERT INTO voice_phrase_alignments
                (phrase_id, voice_asset_id, start_time, end_time, duration, alignment_source, confidence)
            VALUES (?, ?, 0, ?, ?, 'voice_duration_measurement', 0.7)
            """,
            (phrase_id, voice_asset_id, measured["duration"], measured["duration"]),
        )
        conn.execute(
            """
            UPDATE lyric_phrases
            SET voice_audio_path = ?, voice_duration = ?, final_timing_source = 'voice_duration_measurement_pending_human_approval'
            WHERE phrase_id = ?
            """,
            (str(managed), measured["duration"], phrase_id),
        )
    payload = {"voice_asset_id": voice_asset_id, **measured, "silence": silence}
    write_audit("voice_audio_measured", "lyric_phrases", str(phrase_id), "Voice audio imported and duration measured.", payload)
    return True, "Voice audio imported and duration measured.", payload


def voice_sync_summary() -> dict[str, Any]:
    initialize_database()
    with connect() as conn:
        rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT p.phrase_id, p.phrase_index, p.final_start_time, p.final_end_time,
                       p.voice_duration, p.voice_audio_path, p.caption_text,
                       a.voice_asset_id, a.duration AS asset_duration
                FROM lyric_phrases p
                LEFT JOIN voice_audio_assets a ON a.phrase_id = p.phrase_id
                ORDER BY p.phrase_index
                """
            ).fetchall()
        ]
    records = []
    for row in rows:
        target = float(row["final_end_time"]) - float(row["final_start_time"])
        measured = float(row.get("asset_duration") or row.get("voice_duration") or 0)
        diff = measured - target if measured else 0
        pct = (diff / target * 100) if target else 0
        records.append(
            {
                **row,
                "target_duration": target,
                "measured_voice_duration": measured,
                "difference_seconds": diff,
                "difference_percent": pct,
                "silence_allowance": 0.35,
                "sync_classification": classify_voice_sync(target, measured),
            }
        )
    return {
        "status": "not_tested_no_voice_audio" if not any(row.get("voice_asset_id") for row in records) else "voice_audio_imported_needs_review",
        "records": records,
        "imported_voice_file_count": sum(1 for row in records if row.get("voice_asset_id")),
        "measured_voice_count": sum(1 for row in records if row.get("measured_voice_duration")),
        "synchronized_voice_count": sum(1 for row in records if row.get("sync_classification") == "synced"),
    }


def lipsync_readiness_summary() -> dict[str, Any]:
    initialize_database()
    with connect() as conn:
        rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT phrase_id, phrase_index, approved_display_text, display_status,
                       timing_review_status, listening_sync_status,
                       lipsync_timing_locked, final_timing_source
                FROM lyric_phrases
                ORDER BY phrase_index
                """
            ).fetchall()
        ]
    ready = []
    blocked = []
    for row in rows:
        reasons = []
        if row["display_status"] != "approved_unicode" or not row["approved_display_text"]:
            reasons.append("APPROVED_UNICODE_MISSING")
        if not row["lipsync_timing_locked"]:
            reasons.append("PHRASE_TIMING_NOT_LOCKED")
        if row["timing_review_status"] not in {"accepted_from_local_boundary_analysis", "manually_approved"}:
            reasons.append("TIMING_REVIEW_REQUIRED")
        if row.get("listening_sync_status") != "correct_line_verified":
            reasons.append("blocked_on_phrase_listening_review")
        if reasons:
            blocked.append({"phrase_id": row["phrase_id"], "phrase_index": row["phrase_index"], "reasons": reasons})
        else:
            ready.append({"phrase_id": row["phrase_id"], "phrase_index": row["phrase_index"]})
    return {
        "phrase_timing_level": "phrase_boundary_local_analysis",
        "caption_timing_status": "auto_boundary_unverified",
        "readiness_status": "ready" if not blocked else "blocked_on_phrase_listening_review",
        "phoneme_timing_required_for_infinitetalk": False,
        "note": "InfiniteTalk is driven by the exact approved audio waveform; phrase boundaries select the correct audio segment.",
        "ready_phrase_count": len(ready),
        "blocked_phrase_count": len(blocked),
        "ready": ready,
        "blocked": blocked,
    }


def classify_voice_sync(target: float, measured: float) -> str:
    if measured <= 0:
        return "missing_audio"
    diff = abs(measured - target)
    pct = diff / max(target, 0.001)
    if diff <= 0.12 or pct <= 0.03:
        return "synced"
    if diff <= 0.35:
        return "acceptable_with_padding" if measured < target else "acceptable_with_silence_trim"
    if pct <= 0.15:
        return "minor_duration_mismatch"
    return "major_duration_mismatch"


def export_final_captions() -> dict[str, str]:
    initialize_database()
    FINAL_CAPTION_ROOT.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        rows = [dict(row) for row in conn.execute("SELECT * FROM lyric_phrases ORDER BY phrase_index").fetchall()]
    srt = FINAL_CAPTION_ROOT / "CAPTIONS_FINAL_TIMING.srt"
    vtt = FINAL_CAPTION_ROOT / "CAPTIONS_FINAL_TIMING.vtt"
    ass = FINAL_CAPTION_ROOT / "CAPTIONS_FINAL_TIMING.ass"
    json_path = FINAL_CAPTION_ROOT / "CAPTIONS_FINAL_TIMING.json"
    srt.write_text(_render_srt(rows), encoding="utf-8")
    vtt.write_text(_render_vtt(rows), encoding="utf-8")
    ass.write_text(_render_ass(rows), encoding="utf-8")
    json_path.write_text(json.dumps({"timing_authority": "lyric_phrases", "phrases": rows}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"srt": str(srt), "vtt": str(vtt), "ass": str(ass), "json": str(json_path)}


def rebuild_caption_v2() -> dict[str, Any]:
    initialize_database()
    FINAL_CAPTION_V2_ROOT.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        rows = [dict(row) for row in conn.execute("SELECT * FROM lyric_phrases ORDER BY phrase_index").fetchall()]
        sources = [dict(row) for row in conn.execute("SELECT * FROM lyric_source_lines ORDER BY line_index").fetchall()]
    blocked = [
        {
            "phrase_id": row["phrase_id"],
            "phrase_index": row["phrase_index"],
            "reason": "APPROVED_UNICODE_MISSING",
            "original_text": row["original_text"],
        }
        for row in rows
        if row.get("display_status") != "approved_unicode" or not row.get("approved_display_text")
    ]
    export_rows = rows if not blocked else [_warning_caption_row(row) for row in rows]
    srt = FINAL_CAPTION_V2_ROOT / "CAPTIONS_FINAL_TIMING.srt"
    vtt = FINAL_CAPTION_V2_ROOT / "CAPTIONS_FINAL_TIMING.vtt"
    ass = FINAL_CAPTION_V2_ROOT / "CAPTIONS_FINAL_TIMING.ass"
    json_path = FINAL_CAPTION_V2_ROOT / "CAPTIONS_FINAL_TIMING.json"
    conversion = FINAL_CAPTION_V2_ROOT / "CONVERSION_STATUS.json"
    timing = FINAL_CAPTION_V2_ROOT / "TIMING_VALIDATION.json"
    blocked_path = FINAL_CAPTION_V2_ROOT / "BLOCKED_PHRASES.json"
    srt.write_text(_render_srt(export_rows), encoding="utf-8")
    vtt.write_text(_render_vtt(export_rows), encoding="utf-8")
    ass.write_text(_render_ass(export_rows), encoding="utf-8")
    json_path.write_text(
        json.dumps(
            {
                "approved_for_production": not blocked,
                "timing_authority": "lyric_phrases",
                "timing_label": "phrase_boundary_local_analysis",
                "phrases": rows,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    conversion.write_text(json.dumps({"source_lines": sources}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    timing.write_text(json.dumps(validate_phrase_timing(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    blocked_path.write_text(json.dumps({"blocked": blocked}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "root": str(FINAL_CAPTION_V2_ROOT),
        "approved_for_production": not blocked,
        "blocked_count": len(blocked),
        "srt": str(srt),
        "vtt": str(vtt),
        "ass": str(ass),
        "json": str(json_path),
        "blocked": str(blocked_path),
    }


def conversion_review_summary() -> dict[str, Any]:
    initialize_database()
    with connect() as conn:
        rows = [dict(row) for row in conn.execute("SELECT * FROM lyric_source_lines ORDER BY line_index").fetchall()]
    return {
        "rows": rows,
        "confirmed_zawgyi": sum(1 for row in rows if row["detected_encoding"] == "zawgyi"),
        "converted_validated": sum(1 for row in rows if row["conversion_status"] == "converted_validated"),
        "needs_review": sum(1 for row in rows if row["review_status"] == "awaiting_review"),
        "approved": sum(1 for row in rows if row["review_status"] == "approved"),
    }


def approve_all_high_confidence_validated() -> dict[str, int]:
    initialize_database()
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM lyric_source_lines
            WHERE detected_encoding = 'zawgyi'
              AND conversion_status = 'converted_validated'
              AND validation_result = 'valid'
              AND detection_confidence >= 0.5
              AND review_status = 'awaiting_review'
            """
        ).fetchall()
        for row in rows:
            conn.execute(
                """
                UPDATE lyric_source_lines
                SET approved_unicode = normalized_unicode, review_status = 'approved'
                WHERE source_line_id = ?
                """,
                (row["source_line_id"],),
            )
    build_lyric_timing_authority()
    return {"approved": len(rows)}


def update_conversion_review(source_line_id: int, action: str, text: str = "") -> tuple[bool, str]:
    initialize_database()
    with connect() as conn:
        row = conn.execute("SELECT * FROM lyric_source_lines WHERE source_line_id = ?", (source_line_id,)).fetchone()
        if not row:
            return False, "Unknown source line."
        if action == "approve":
            value = row["normalized_unicode"]
            status = "approved"
        elif action == "mark_original_unicode":
            value = normalize_burmese(row["original_text"])
            status = "approved"
        elif action == "edit":
            value = normalize_burmese(text)
            status = "approved"
            conn.execute("UPDATE lyric_source_lines SET user_corrected_unicode = ? WHERE source_line_id = ?", (value, source_line_id))
        elif action == "reject":
            value = ""
            status = "rejected"
        else:
            return False, "Invalid action."
        conn.execute(
            "UPDATE lyric_source_lines SET approved_unicode = ?, review_status = ? WHERE source_line_id = ?",
            (value, status, source_line_id),
        )
    build_lyric_timing_authority()
    return True, "Conversion review saved."


def validate_phrase_timing() -> dict[str, Any]:
    initialize_database()
    with connect() as conn:
        rows = [dict(row) for row in conn.execute("SELECT * FROM lyric_phrases ORDER BY phrase_index").fetchall()]
    warnings: list[dict[str, Any]] = []
    previous_end = 0.0
    duration = _probe_audio_duration(MASTER_AUDIO)
    for row in rows:
        start = float(row["final_start_time"])
        end = float(row["final_end_time"])
        if end <= start:
            warnings.append({"phrase_id": row["phrase_id"], "warning": "ZERO_OR_REVERSED_RANGE"})
        if start < previous_end:
            warnings.append({"phrase_id": row["phrase_id"], "warning": "OVERLAP"})
        if end > duration:
            warnings.append({"phrase_id": row["phrase_id"], "warning": "BEYOND_SONG_DURATION"})
        previous_end = max(previous_end, end)
    return {
        "timing_label": "phrase_boundary_local_analysis",
        "word_aligned": False,
        "syllable_aligned": False,
        "phoneme_aligned": False,
        "phrase_count": len(rows),
        "warnings": warnings,
        "valid": not warnings,
    }


def _record_source_lines(source: Path, raw_lines: list[str]) -> list[dict[str, Any]]:
    source_rel = str(source.relative_to(REPO_ROOT))
    source_is_zawgyi = "zawgyi" in source.name.lower()
    records: list[dict[str, Any]] = []
    with connect() as conn:
        existing_reviews = {
            row["original_sha256"]: dict(row)
            for row in conn.execute(
                "SELECT original_sha256, approved_unicode, user_corrected_unicode, review_status FROM lyric_source_lines WHERE source_path = ?",
                (source_rel,),
            ).fetchall()
        }
        conn.execute("DELETE FROM voice_phrase_alignments")
        conn.execute("DELETE FROM voice_audio_assets")
        conn.execute("DELETE FROM lyric_syllable_markers")
        conn.execute("DELETE FROM lyric_phrases")
        conn.execute("DELETE FROM lyric_source_lines WHERE source_path = ?", (source_rel,))
        for index, original in enumerate(raw_lines, start=1):
            detected = detect_encoding(original)
            is_section = _is_section_label(original)
            has_myanmar = _has_myanmar(original)
            confirmed_zawgyi = has_myanmar and not is_section and (detected["encoding"] == "zawgyi" or source_is_zawgyi)
            conversion = {"converted": original, "changed": False, "uncertain": False, "converter": "not_needed"}
            action = "preserve_original"
            if confirmed_zawgyi:
                conversion = zawgyi_to_unicode(original, confidence=float(detected["confidence"]))
                action = "confirmed_zawgyi_to_unicode"
            elif detected["encoding"] == "uncertain":
                action = "preserve_uncertain_encoding"
            unicode_text = conversion["converted"] if confirmed_zawgyi else original
            normalized = normalize_burmese(unicode_text)
            validation = conversion.get("validation", {"result": "not_converted", "warnings": [], "converted_hash": ""})
            conversion_status = conversion.get("status", "not_converted")
            review_status = "awaiting_review"
            approved_unicode = ""
            user_corrected_unicode = ""
            if not confirmed_zawgyi and detected["encoding"] == "unicode":
                conversion_status = "validated_original_unicode"
                review_status = "approved"
                approved_unicode = normalized
            existing = existing_reviews.get(hashlib.sha256(original.encode("utf-8")).hexdigest(), {})
            if existing.get("review_status") in {"approved", "rejected"}:
                approved_unicode = existing.get("approved_unicode", approved_unicode)
                user_corrected_unicode = existing.get("user_corrected_unicode", "")
                review_status = existing.get("review_status", review_status)
            cursor = conn.execute(
                """
                INSERT INTO lyric_source_lines
                    (source_path, line_index, original_text, original_sha256, detected_encoding,
                     zawgyi_probability, detection_confidence, conversion_action, unicode_text,
                     normalized_unicode, conversion_uncertain, is_section_label, source_category,
                     conversion_engine, conversion_engine_version, conversion_status,
                     validation_result, validation_warnings, converted_sha256,
                     approved_unicode, user_corrected_unicode, review_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_rel,
                    index,
                    original,
                    hashlib.sha256(original.encode("utf-8")).hexdigest(),
                    "zawgyi" if confirmed_zawgyi else detected["encoding"],
                    float(detected["zawgyi_probability"]),
                    float(detected["confidence"]),
                    action,
                    unicode_text,
                    normalized,
                    1 if conversion.get("uncertain") else 0,
                    1 if is_section else 0,
                    _source_category(original, index),
                    conversion.get("converter", "not_needed"),
                    conversion.get("converter_version", ""),
                    conversion_status,
                    validation.get("result", "unknown"),
                    json.dumps(validation.get("warnings", []), ensure_ascii=False),
                    validation.get("converted_hash", hashlib.sha256(normalized.encode("utf-8")).hexdigest()),
                    approved_unicode,
                    user_corrected_unicode,
                    review_status,
                ),
            )
            records.append(
                {
                    "source_line_id": int(cursor.lastrowid),
                    "source_path": source_rel,
                    "line_index": index,
                    "original_text": original,
                    "detected_encoding": "zawgyi" if confirmed_zawgyi else detected["encoding"],
                    "zawgyi_probability": detected["zawgyi_probability"],
                    "detection_confidence": detected["confidence"],
                    "conversion_action": action,
                    "unicode_text": unicode_text,
                    "normalized_unicode": normalized,
                    "conversion_uncertain": bool(conversion.get("uncertain")),
                    "is_section_label": bool(is_section),
                    "source_category": _source_category(original, index),
                    "conversion_engine": conversion.get("converter", "not_needed"),
                    "conversion_engine_version": conversion.get("converter_version", ""),
                    "conversion_status": conversion_status,
                    "validation_result": validation.get("result", "unknown"),
                    "validation_warnings": validation.get("warnings", []),
                    "approved_unicode": approved_unicode,
                    "user_corrected_unicode": user_corrected_unicode,
                    "review_status": review_status,
                }
            )
    return records


def _record_phrase_timing(
    lyric_lines: list[dict[str, Any]],
    vocal_phrases: list[dict[str, Any]],
    boundary_data: dict[str, Any],
    audio_duration: float,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    phrase_count = max(len(lyric_lines), 1)
    source_audio = boundary_data.get("source") or str(MASTER_AUDIO)
    with connect() as conn:
        for idx, line in enumerate(lyric_lines, start=1):
            boundary = vocal_phrases[idx - 1] if idx - 1 < len(vocal_phrases) else None
            if boundary:
                start = float(boundary["start"])
                end = float(boundary["end"])
                timing_source = "phrase_boundary_local_analysis"
                confidence = 0.74
            else:
                start = audio_duration * ((idx - 1) / phrase_count)
                end = audio_duration * (idx / phrase_count)
                timing_source = "duration_proportional_fallback"
                confidence = 0.25
            display = resolve_display_text(line)
            caption = " / ".join(caption_safe_lines(display)) if display else ""
            helper = pronunciation_helper(display) if display else ""
            cursor = conn.execute(
                """
                INSERT INTO lyric_phrases
                    (source_line_id, phrase_index, original_text, normalized_unicode,
                     pronunciation_helper, caption_text, start_time, end_time,
                     timing_source, alignment_confidence, vocal_audio_path,
                     final_start_time, final_end_time, final_timing_source,
                     lipsync_timing_locked, approved_display_text, display_status,
                     timing_review_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
                """,
                (
                    line["source_line_id"],
                    idx,
                    line["original_text"],
                    display or line["normalized_unicode"],
                    helper,
                    caption,
                    start,
                    end,
                    timing_source,
                    confidence,
                    source_audio,
                    start,
                    end,
                    timing_source,
                    display,
                    "approved_unicode" if display else "unavailable_for_production",
                    "accepted_from_local_boundary_analysis",
                ),
            )
            row = {
                "phrase_id": int(cursor.lastrowid),
                "source_line_id": line["source_line_id"],
                "phrase_index": idx,
                "original_text": line["original_text"],
                "normalized_unicode": display or line["normalized_unicode"],
                "pronunciation_helper": helper,
                "caption_text": caption,
                "start_time": start,
                "end_time": end,
                "timing_source": timing_source,
                "alignment_confidence": confidence,
                "vocal_audio_path": source_audio,
                "final_start_time": start,
                "final_end_time": end,
                "final_timing_source": timing_source,
                "lipsync_timing_locked": True,
                "approved_display_text": display,
                "display_status": "approved_unicode" if display else "unavailable_for_production",
                "timing_review_status": "accepted_from_local_boundary_analysis",
            }
            rows.append(row)
            _insert_syllable_markers(conn, row)
    return rows


def resolve_display_text(line: dict[str, Any]) -> str:
    if line.get("user_corrected_unicode"):
        return line["user_corrected_unicode"]
    if line.get("approved_unicode"):
        return line["approved_unicode"]
    if line.get("review_status") == "approved" and line.get("conversion_status") in {"converted_validated", "validated_original_unicode"}:
        return line["normalized_unicode"]
    return ""


def _find_lyric_source() -> Path:
    candidates = sorted((REPO_ROOT / "lyrics").glob("*.txt")) if (REPO_ROOT / "lyrics").exists() else []
    if not candidates:
        raise FileNotFoundError("No lyric .txt file found.")
    zawgyi = [path for path in candidates if "zawgyi" in path.name.lower()]
    return zawgyi[0] if zawgyi else candidates[0]


def _read_vocal_boundaries() -> dict[str, Any]:
    if VOCAL_BOUNDARY_PATH.exists():
        return json.loads(VOCAL_BOUNDARY_PATH.read_text(encoding="utf-8"))
    return {"source": str(MASTER_AUDIO), "phrases": []}


def _probe_audio_duration(path: Path) -> float:
    if not path.exists():
        return 0.0
    result = subprocess.run(
        [ffprobe_path(), "-v", "error", "-show_format", "-print_format", "json", str(path)],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    data = json.loads(result.stdout)
    return float(data.get("format", {}).get("duration") or 0)


def extract_lipsync_audio_for_phrase(run_id: int, shot_id: str, phrase: dict[str, Any]) -> dict[str, Any]:
    root = ENGINE_ROOT / "lipsync" / str(run_id) / shot_id
    root.mkdir(parents=True, exist_ok=True)
    start = float(phrase["final_start_time"])
    end = float(phrase["final_end_time"])
    duration = max(end - start, 0.25)
    full_mix = root / "FULL_MIX_SEGMENT.wav"
    vocal = root / "VOCAL_SEGMENT.wav"
    log = root / "AUDIO_BUILD_LOG.txt"
    command = [
        ffmpeg_path(),
        "-y",
        "-ss",
        f"{start:.3f}",
        "-t",
        f"{duration:.3f}",
        "-i",
        str(MASTER_AUDIO),
        "-ar",
        "44100",
        "-ac",
        "1",
        str(full_mix),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    log.write_text("$ " + " ".join(command) + "\n" + result.stdout + result.stderr + "\n", encoding="utf-8")
    if full_mix.exists():
        shutil.copyfile(full_mix, vocal)
    (root / "LYRICS.txt").write_text(phrase["original_text"] + "\n", encoding="utf-8")
    (root / "PRONUNCIATION_HELPER.txt").write_text(phrase["pronunciation_helper"] + "\n", encoding="utf-8")
    metadata = {
        "phrase_id": phrase["phrase_id"],
        "phrase_index": phrase["phrase_index"],
        "shot_id": shot_id,
        "source_audio": str(MASTER_AUDIO),
        "start_time": start,
        "end_time": end,
        "duration": duration,
        "timing_source": phrase["final_timing_source"],
        "lipsync_timing_locked": bool(phrase["lipsync_timing_locked"]),
        "full_mix_segment": str(full_mix),
        "vocal_segment": str(vocal),
        "ffmpeg_returncode": result.returncode,
    }
    (root / "JOB_MANIFEST.yaml").write_text(_manifest_yaml(metadata), encoding="utf-8")
    (root / "AUDIO_SEGMENT_METADATA.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return metadata


def _render_srt(rows: list[dict[str, Any]]) -> str:
    blocks = []
    for index, row in enumerate(rows, start=1):
        blocks.append(f"{index}\n{_srt_tc(row['final_start_time'])} --> {_srt_tc(row['final_end_time'])}\n{row['caption_text']}\n")
    return "\n".join(blocks)


def _render_vtt(rows: list[dict[str, Any]]) -> str:
    return "WEBVTT\n\n" + "\n".join(
        f"{_vtt_tc(row['final_start_time'])} --> {_vtt_tc(row['final_end_time'])}\n{row['caption_text']}\n" for row in rows
    )


def _render_ass(rows: list[dict[str, Any]]) -> str:
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Burmese,Noto Sans Myanmar,54,&H00F7F0E8,&H000000FF,&H00101010,&H99000000,0,0,0,0,100,100,0,0,1,2,1,2,90,90,72,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for row in rows:
        caption = str(row["caption_text"]).replace("/", "\\N")
        events.append(
            f"Dialogue: 0,{_ass_tc(row['final_start_time'])},{_ass_tc(row['final_end_time'])},Burmese,,0,0,0,,{caption}"
        )
    return header + "\n".join(events) + "\n"


def _render_authority_md(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Lyric Timing Authority",
        "",
        f"Source: `{summary['source_path']}`",
        f"Timing source: `{summary['timing_source']}`",
        f"Word-level ASR: `{summary['word_level_asr']}`",
        "",
        "| # | Start | End | Original | Caption | Timing | Confidence |",
        "|---|---:|---:|---|---|---|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['phrase_index']} | {row['final_start_time']:.2f} | {row['final_end_time']:.2f} | {row['original_text']} | {row['caption_text']} | {row['final_timing_source']} | {row['alignment_confidence']:.2f} |"
        )
    return "\n".join(lines) + "\n"


def _manifest_yaml(metadata: dict[str, Any]) -> str:
    return "\n".join(f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in metadata.items()) + "\n"


def _warning_caption_row(row: dict[str, Any]) -> dict[str, Any]:
    copy = dict(row)
    copy["caption_text"] = f"REVIEW REQUIRED: phrase {row['phrase_index']} Unicode approval missing"
    return copy


def _managed_voice_copy(path: Path, phrase_id: int) -> Path:
    root = VOICE_IMPORT_ROOT / f"phrase-{phrase_id}"
    root.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    managed = root / f"voice-import-{_sha256(path)[:12]}{suffix}"
    if not managed.exists():
        shutil.copyfile(path, managed)
    return managed


def estimate_silence(path: Path) -> dict[str, float]:
    # v1.0.3 records the field but does not make acoustic sync claims from it.
    # A later RMS scan can replace this without changing the data model.
    return {"leading_silence": 0.0, "trailing_silence": 0.0}


def _insert_syllable_markers(conn, row: dict[str, Any]) -> None:
    syllables = segment_syllables(row.get("approved_display_text") or row.get("normalized_unicode") or "")
    total = max(len(syllables), 1)
    for index, syllable in enumerate(syllables, start=1):
        conn.execute(
            """
            INSERT INTO lyric_syllable_markers
                (phrase_id, syllable_index, syllable_text, relative_estimated_position, alignment_status)
            VALUES (?, ?, ?, ?, 'estimated_within_phrase')
            """,
            (row["phrase_id"], index, syllable, (index - 0.5) / total),
        )


def _source_category(text: str, line_index: int) -> str:
    stripped = text.strip()
    if not stripped:
        return "blank"
    if _is_section_label(text):
        return "section"
    if line_index == 1:
        return "title"
    if "ေတးေရး" in text or "တေးရေး" in text:
        return "credit"
    return "lyric"


def _has_myanmar(text: str) -> bool:
    return any("\u1000" <= char <= "\u109f" or "\uaa60" <= char <= "\uaa7f" for char in text)


def _is_section_label(text: str) -> bool:
    stripped = text.strip()
    return not stripped or bool(re.fullmatch(r"[A-Za-z0-9 ]+:", stripped))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _srt_tc(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _vtt_tc(seconds: float) -> str:
    return _srt_tc(seconds).replace(",", ".")


def _ass_tc(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"
