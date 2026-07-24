from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.burmese.alignment_service import rough_line_timing
from app.burmese.caption_service import caption_safe_lines
from app.burmese.encoding_detector import detect_encoding
from app.burmese.lyric_segmenter import segment_lyrics
from app.burmese.normalization_service import normalize_burmese
from app.burmese.pronunciation_service import pronunciation_helper
from app.burmese.syllable_segmenter import segment_syllables
from app.burmese.terminology_memory import approved_pronunciation_overrides
from app.burmese.typography_service import installed_burmese_fonts
from app.config import ENGINE_ROOT, REPO_ROOT
from app.services.db import connect, initialize_database
from app.services.director_workspace_service import list_caption_lines
from app.services.lyric_timing_service import build_lyric_timing_authority, lyric_timing_summary
from app.services.v09_studio_service import export_caption_formats


def build_burmese_timeline(duration: float = 193.76) -> dict[str, Any]:
    authority = build_lyric_timing_authority()
    if authority["phrases"]:
        _sync_caption_lines_from_authority()
        return {
            "records": authority["phrases"],
            "fonts": installed_burmese_fonts(),
            "original_preserved": True,
            "timing_authority": authority["summary"],
        }
    initialize_database()
    lyric_text = read_lyrics()
    lines = segment_lyrics(lyric_text)
    timings = rough_line_timing(lines, duration)
    overrides = approved_pronunciation_overrides()
    records = []
    with connect() as conn:
        for index, item in enumerate(timings):
            original = item["line"]
            detected = detect_encoding(original)
            normalized = normalize_burmese(original)
            helper = pronunciation_helper(normalized, overrides)
            caption = " / ".join(caption_safe_lines(normalized))
            syllables = segment_syllables(normalized)
            conn.execute(
                """
                INSERT INTO burmese_caption_lines
                    (source_path, line_index, original_text, normalized_unicode,
                     pronunciation_helper, caption_text, translation_note,
                     start_time, end_time, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft')
                """,
                (
                    "lyrics",
                    index,
                    original,
                    normalized,
                    helper,
                    caption,
                    "Meaning pending human/director review.",
                    seconds_to_timecode(item["start"]),
                    seconds_to_timecode(item["end"]),
                ),
            )
            records.append(
                {
                    "line_index": index,
                    "original_text": original,
                    "detected_encoding": detected,
                    "normalized_unicode": normalized,
                    "syllables": syllables,
                    "pronunciation_helper": helper,
                    "caption_text": caption,
                    "meaning": "pending",
                    "emotional_meaning": "pending",
                    "timecode": {"start": item["start"], "end": item["end"]},
                    "approval_state": "draft",
                }
            )
    root = ENGINE_ROOT / "burmese-language"
    root.mkdir(parents=True, exist_ok=True)
    timeline = {"records": records, "fonts": installed_burmese_fonts(), "original_preserved": True}
    (root / "BURMESE_LYRIC_TIMELINE.json").write_text(json.dumps(timeline, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (root / "BURMESE_LYRIC_TIMELINE.md").write_text(render_timeline(records), encoding="utf-8")
    export_caption_formats()
    return timeline


def burmese_language_summary() -> dict[str, Any]:
    records = list_caption_lines()
    timing = lyric_timing_summary()
    return {
        "line_count": len(records),
        "phrase_count": timing["phrase_count"],
        "locked_count": timing["locked_count"],
        "fonts": installed_burmese_fonts(),
        "timeline_path": str(ENGINE_ROOT / "burmese-language" / "BURMESE_LYRIC_TIMELINE.json"),
        "timing_authority_path": timing["authority_path"],
        "caption_root": timing["caption_root"],
        "records": records[:100],
        "phrases": timing["records"],
    }


def _sync_caption_lines_from_authority() -> None:
    initialize_database()
    with connect() as conn:
        phrases = conn.execute(
            """
            SELECT p.*, l.source_path
            FROM lyric_phrases p
            JOIN lyric_source_lines l ON l.source_line_id = p.source_line_id
            ORDER BY p.phrase_index
            """
        ).fetchall()
        conn.execute("DELETE FROM burmese_caption_lines")
        for phrase in phrases:
            conn.execute(
                """
                INSERT INTO burmese_caption_lines
                    (source_path, line_index, original_text, normalized_unicode,
                     pronunciation_helper, caption_text, translation_note,
                     start_time, end_time, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft')
                """,
                (
                    phrase["source_path"],
                    phrase["phrase_index"],
                    phrase["original_text"],
                    phrase["normalized_unicode"],
                    phrase["pronunciation_helper"],
                    phrase["caption_text"],
                    f"timing_source={phrase['final_timing_source']}; confidence={phrase['alignment_confidence']}",
                    seconds_to_timecode(float(phrase["final_start_time"])),
                    seconds_to_timecode(float(phrase["final_end_time"])),
                ),
            )


def read_lyrics() -> str:
    candidates = list((REPO_ROOT / "lyrics").glob("*")) if (REPO_ROOT / "lyrics").exists() else []
    for path in candidates:
        if path.is_file() and path.suffix.lower() in {".txt", ".md", ".srt"}:
            return path.read_text(encoding="utf-8", errors="ignore")
    current = list_caption_lines()
    if current:
        return "\n".join(row["original_text"] for row in current)
    return ""


def seconds_to_timecode(seconds: float) -> str:
    minutes = int(seconds // 60)
    sec = seconds - minutes * 60
    return f"{minutes:02d}:{sec:05.2f}"


def render_timeline(records: list[dict[str, Any]]) -> str:
    lines = ["# Burmese Lyric Timeline", "", "| # | Original | Unicode | Pronunciation | Caption | Time |", "|---|---|---|---|---|---|"]
    for record in records:
        time = f"{record['timecode']['start']:.2f}-{record['timecode']['end']:.2f}"
        lines.append(
            f"| {record['line_index']} | {record['original_text']} | {record['normalized_unicode']} | {record['pronunciation_helper']} | {record['caption_text']} | {time} |"
        )
    return "\n".join(lines) + "\n"
