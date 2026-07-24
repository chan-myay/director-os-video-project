from __future__ import annotations

import csv
import json
import math
import struct
import zlib
from pathlib import Path
from typing import Any, Optional

from app.config import ENGINE_ROOT, REPO_ROOT
from app.services.audit_service import write_audit
from app.services.autonomous_director_service import LATEST_PLAN, director_status, run_autonomous_director
from app.services.db import connect, initialize_database
from app.services.engine_reader import read_text


PREVIS_ROOT = ENGINE_ROOT / "previs" / "latest"
ANIMATIC_ROOT = ENGINE_ROOT / "animatics" / "latest"
CAPTION_ROOT = ENGINE_ROOT / "captions" / "latest"


def sync_workspace_from_latest_plan() -> dict[str, Any]:
    initialize_database()
    status = director_status()
    if not status["has_plan"]:
        status = run_autonomous_director("", REPO_ROOT, dry_run=True)
    state = status["state"]
    storyboard = status["storyboard"]
    run_id = _record_run(state)
    cards = storyboard.get("shots", [])
    PREVIS_ROOT.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        for shot in cards:
            shot_number = shot["shot_number"]
            raster_path = PREVIS_ROOT / f"{shot_number}.png"
            write_previs_png(raster_path, shot)
            conn.execute(
                """
                INSERT INTO storyboard_cards
                    (run_id, shot_number, title, song_section, timecode_start,
                     timecode_end, purpose, framing, lens, camera_movement,
                     lighting, production_design, performer_action, exact_movement,
                     identity_risk, body_motion_risk, recommended_renderer,
                     fallback_renderer, status, frame_path, raster_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'planned', ?, ?)
                ON CONFLICT(shot_number) DO UPDATE SET
                    run_id = excluded.run_id,
                    title = excluded.title,
                    song_section = excluded.song_section,
                    timecode_start = excluded.timecode_start,
                    timecode_end = excluded.timecode_end,
                    purpose = excluded.purpose,
                    framing = excluded.framing,
                    lens = excluded.lens,
                    camera_movement = excluded.camera_movement,
                    lighting = excluded.lighting,
                    production_design = excluded.production_design,
                    performer_action = excluded.performer_action,
                    exact_movement = excluded.exact_movement,
                    identity_risk = excluded.identity_risk,
                    body_motion_risk = excluded.body_motion_risk,
                    recommended_renderer = excluded.recommended_renderer,
                    fallback_renderer = excluded.fallback_renderer,
                    frame_path = excluded.frame_path,
                    raster_path = excluded.raster_path,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    run_id,
                    shot_number,
                    shot["title"],
                    shot["song_section"],
                    shot["timecode_start"],
                    shot["timecode_end"],
                    shot["purpose"],
                    shot["framing"],
                    shot["lens"],
                    shot["camera_position_movement"],
                    shot["lighting"],
                    shot["production_design"],
                    shot["performer_action"],
                    shot["exact_movement"],
                    shot["identity_risk"],
                    shot["body_motion_risk"],
                    shot["recommended_renderer"],
                    shot["fallback_renderer"],
                    f"storyboards/latest/frames/{shot_number}.svg",
                    str(raster_path),
                ),
            )
            conn.execute(
                """
                INSERT INTO previs_assets (shot_number, asset_type, path, width, height)
                VALUES (?, 'raster_previs_png', ?, 1280, 720)
                """,
                (shot_number, str(raster_path)),
            )
            strategy = renderer_strategy_for_shot(shot)
            conn.execute(
                """
                INSERT INTO renderer_strategy_items
                    (shot_number, best_renderer, fallback_renderer, local_alternative,
                     required_inputs, privacy_risk, cost_risk, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'planned')
                """,
                (
                    shot_number,
                    strategy["best_renderer"],
                    strategy["fallback_renderer"],
                    strategy["local_alternative"],
                    json.dumps(strategy["required_inputs"], ensure_ascii=False),
                    strategy["privacy_risk"],
                    strategy["cost_risk"],
                ),
            )
    animatic = build_animatic(run_id)
    caption_count = seed_burmese_caption_workspace()
    write_exports()
    write_audit(
        "director_workspace_synced",
        "director_workspace",
        str(run_id),
        "v0.8 workspace synced from autonomous director plan.",
        {"cards": len(cards), "animatic": animatic["path"], "captions": caption_count},
    )
    return workspace_summary()


def workspace_summary() -> dict[str, Any]:
    initialize_database()
    with connect() as conn:
        card_count = conn.execute("SELECT COUNT(*) FROM storyboard_cards").fetchone()[0]
        approved = conn.execute("SELECT COUNT(*) FROM storyboard_cards WHERE status = 'approved'").fetchone()[0]
        rejected = conn.execute("SELECT COUNT(*) FROM storyboard_cards WHERE status = 'rejected'").fetchone()[0]
        refine = conn.execute("SELECT COUNT(*) FROM storyboard_cards WHERE status = 'needs_refine'").fetchone()[0]
        comments = conn.execute("SELECT COUNT(*) FROM storyboard_comments").fetchone()[0]
        previs = conn.execute("SELECT COUNT(*) FROM previs_assets WHERE asset_type = 'raster_previs_png'").fetchone()[0]
        animatic = conn.execute("SELECT * FROM animatics ORDER BY animatic_id DESC LIMIT 1").fetchone()
    return {
        "card_count": card_count,
        "approved": approved,
        "rejected": rejected,
        "needs_refine": refine,
        "comments": comments,
        "previs_count": previs,
        "animatic": dict(animatic) if animatic else None,
        "next_action": "Review storyboard cards and mark F01/F06 motion-heavy shots for motion-reference capture.",
    }


def list_storyboard_cards(status_filter: str = "") -> list[dict[str, Any]]:
    initialize_database()
    sync_if_empty()
    query = "SELECT * FROM storyboard_cards"
    params: tuple[Any, ...] = ()
    if status_filter:
        query += " WHERE status = ?"
        params = (status_filter,)
    query += " ORDER BY CAST(SUBSTR(shot_number, 2) AS INTEGER)"
    with connect() as conn:
        rows = conn.execute(query, params).fetchall()
        cards = []
        for row in rows:
            card = dict(row)
            card["comments"] = [
                dict(comment)
                for comment in conn.execute(
                    "SELECT * FROM storyboard_comments WHERE shot_number = ? ORDER BY comment_id DESC",
                    (card["shot_number"],),
                ).fetchall()
            ]
            card["decisions"] = [
                dict(decision)
                for decision in conn.execute(
                    "SELECT * FROM storyboard_decisions WHERE shot_number = ? ORDER BY decision_id DESC",
                    (card["shot_number"],),
                ).fetchall()
            ]
            cards.append(card)
    return cards


def get_storyboard_card(shot_number: str) -> Optional[dict[str, Any]]:
    cards = [card for card in list_storyboard_cards() if card["shot_number"] == shot_number]
    return cards[0] if cards else None


def decide_storyboard_card(shot_number: str, decision: str, reason: str = "") -> tuple[bool, str]:
    if decision not in {"approved", "rejected", "needs_refine", "planned"}:
        return False, "Invalid storyboard decision."
    initialize_database()
    with connect() as conn:
        row = conn.execute("SELECT shot_number FROM storyboard_cards WHERE shot_number = ?", (shot_number,)).fetchone()
        if not row:
            return False, "Unknown storyboard card."
        conn.execute(
            "UPDATE storyboard_cards SET status = ?, version = version + 1, updated_at = CURRENT_TIMESTAMP WHERE shot_number = ?",
            (decision, shot_number),
        )
        conn.execute(
            "INSERT INTO storyboard_decisions (shot_number, decision, reason) VALUES (?, ?, ?)",
            (shot_number, decision, reason),
        )
    write_audit(
        "storyboard_card_decision",
        "storyboard_cards",
        shot_number,
        f"Storyboard card {shot_number} marked {decision}.",
        {"reason": reason},
    )
    write_exports()
    return True, "Storyboard decision saved."


def comment_storyboard_card(shot_number: str, comment: str) -> tuple[bool, str]:
    comment = comment.strip()
    if not comment:
        return False, "Comment is required."
    initialize_database()
    with connect() as conn:
        row = conn.execute("SELECT shot_number FROM storyboard_cards WHERE shot_number = ?", (shot_number,)).fetchone()
        if not row:
            return False, "Unknown storyboard card."
        conn.execute("INSERT INTO storyboard_comments (shot_number, comment) VALUES (?, ?)", (shot_number, comment))
    write_audit("storyboard_comment", "storyboard_cards", shot_number, f"Comment added to {shot_number}.", {})
    return True, "Comment saved."


def build_animatic(run_id: int = 0) -> dict[str, Any]:
    cards = list_storyboard_cards()
    ANIMATIC_ROOT.mkdir(parents=True, exist_ok=True)
    path = ANIMATIC_ROOT / "ANIMATIC.html"
    duration = sum(tc_duration(card["timecode_start"], card["timecode_end"]) for card in cards)
    path.write_text(animatic_html(cards), encoding="utf-8")
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO animatics (run_id, path, frame_count, duration, backend, status)
            VALUES (?, ?, ?, ?, 'html_timeline', 'created')
            """,
            (run_id, str(path), len(cards), duration),
        )
        animatic_id = int(cursor.lastrowid)
    return {"animatic_id": animatic_id, "path": str(path), "frame_count": len(cards), "duration": duration}


def seed_burmese_caption_workspace() -> int:
    CAPTION_ROOT.mkdir(parents=True, exist_ok=True)
    lyric_files = sorted((REPO_ROOT / "lyrics").glob("*.txt")) if (REPO_ROOT / "lyrics").exists() else []
    if not lyric_files:
        return 0
    source = lyric_files[0]
    lines = [line.strip() for line in source.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip()]
    with connect() as conn:
        existing = conn.execute("SELECT COUNT(*) FROM burmese_caption_lines").fetchone()[0]
        if existing:
            return existing
        for idx, line in enumerate(lines, start=1):
            conn.execute(
                """
                INSERT INTO burmese_caption_lines
                    (source_path, line_index, original_text, normalized_unicode,
                     pronunciation_helper, caption_text, translation_note, status)
                VALUES (?, ?, ?, ?, '', ?, '', 'draft')
                """,
                (str(source.relative_to(REPO_ROOT)), idx, line, conservative_burmese_normalize(line), conservative_burmese_normalize(line)),
            )
    export_captions()
    return len(lines)


def list_caption_lines() -> list[dict[str, Any]]:
    initialize_database()
    seed_burmese_caption_workspace()
    with connect() as conn:
        rows = conn.execute("SELECT * FROM burmese_caption_lines ORDER BY line_index").fetchall()
    return [dict(row) for row in rows]


def update_caption_line(line_id: int, form: dict[str, str]) -> tuple[bool, str]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM burmese_caption_lines WHERE line_id = ?", (line_id,)).fetchone()
        if not row:
            return False, "Unknown caption line."
        conn.execute(
            """
            UPDATE burmese_caption_lines
            SET pronunciation_helper = ?, caption_text = ?, translation_note = ?,
                start_time = ?, end_time = ?, status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE line_id = ?
            """,
            (
                form.get("pronunciation_helper", ""),
                form.get("caption_text", ""),
                form.get("translation_note", ""),
                form.get("start_time", ""),
                form.get("end_time", ""),
                form.get("status", "draft"),
                line_id,
            ),
        )
    export_captions()
    write_audit("caption_line_updated", "burmese_caption_lines", str(line_id), "Burmese caption line updated.", {})
    return True, "Caption line updated."


def create_voice_test(form: dict[str, str]) -> tuple[bool, str]:
    if not form.get("input_text", "").strip():
        return False, "Input text is required."
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO voice_tests
                (provider, voice_name, input_text, pronunciation_notes,
                 consent_confirmed, cloud_upload_approved, status)
            VALUES (?, ?, ?, ?, ?, ?, 'planned')
            """,
            (
                form.get("provider", "manual"),
                form.get("voice_name", ""),
                form.get("input_text", ""),
                form.get("pronunciation_notes", ""),
                1 if form.get("consent_confirmed") == "on" else 0,
                1 if form.get("cloud_upload_approved") == "on" else 0,
            ),
        )
    write_audit("voice_test_planned", "voice_tests", "latest", "Voice test record created; no API call made.", {})
    return True, "Voice test recorded. No API call was made."


def list_voice_tests() -> list[dict[str, Any]]:
    initialize_database()
    with connect() as conn:
        rows = conn.execute("SELECT * FROM voice_tests ORDER BY voice_test_id DESC").fetchall()
    return [dict(row) for row in rows]


def analyze_motion_reference(motion_id: int) -> tuple[bool, str]:
    initialize_database()
    with connect() as conn:
        motion = conn.execute("SELECT * FROM motion_references WHERE motion_id = ?", (motion_id,)).fetchone()
        if not motion:
            return False, "Unknown motion reference."
        data = dict(motion)
        source = Path(data["source"]).expanduser()
        if not source.is_absolute():
            source = REPO_ROOT / data["source"]
        file_size = source.stat().st_size if source.exists() and source.is_file() else 0
        warnings = []
        if not source.exists() and data["source_type"] == "local_path":
            warnings.append("LOCAL_FILE_MISSING")
        if data["body_framing"] not in {"full-body", "medium-wide"}:
            warnings.append("FRAMING_NOT_PRODUCTION_READY")
        if data["travel_direction"] not in {"left-to-right", "right-to-left"}:
            warnings.append("TRAVEL_DIRECTION_MISSING")
        conn.execute(
            """
            INSERT INTO motion_reference_analysis
                (motion_id, shot_id, source, file_size, analysis_status,
                 inferred_body_framing, inferred_travel_direction, warnings)
            VALUES (?, ?, ?, ?, 'metadata_only', ?, ?, ?)
            """,
            (
                motion_id,
                data["shot_id"],
                data["source"],
                file_size,
                data["body_framing"],
                data["travel_direction"],
                json.dumps(warnings),
            ),
        )
    write_audit("motion_reference_analyzed", "motion_references", str(motion_id), "Motion reference metadata analysis saved.", {"warnings": warnings})
    return True, "Motion reference metadata analysis saved."


def list_motion_analyses() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM motion_reference_analysis ORDER BY analysis_id DESC").fetchall()
    return [dict(row) for row in rows]


def add_research_items(query: str) -> list[dict[str, Any]]:
    query = query.strip() or "mature side-travel performance references lonely blues jazz bar music video"
    links = [
        ("Shot.Cafe search", f"https://shot.cafe/search/{query.replace(' ', '+')}", "composition"),
        ("YouTube search", f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}", "motion"),
        ("Vimeo search", f"https://vimeo.com/search?q={query.replace(' ', '+')}", "motion"),
        ("FilmGrab search", f"https://film-grab.com/?s={query.replace(' ', '+')}", "cinematography"),
    ]
    with connect() as conn:
        for title, url, category in links:
            conn.execute(
                """
                INSERT INTO research_items (query, title, url, category, notes, shot_pack_id)
                VALUES (?, ?, ?, ?, ?, 'F01_side_travel_dance')
                """,
                (query, title, url, category, "Link-only research lead. Store notes/timecodes; do not copy or rehost media."),
            )
    return list_research_items()


def list_research_items() -> list[dict[str, Any]]:
    initialize_database()
    with connect() as conn:
        rows = conn.execute("SELECT * FROM research_items ORDER BY item_id DESC LIMIT 50").fetchall()
    return [dict(row) for row in rows]


def write_exports() -> None:
    cards = list_storyboard_cards()
    export_json = LATEST_PLAN / "STORYBOARD_WORKSPACE.json"
    export_csv = LATEST_PLAN / "STORYBOARD_WORKSPACE.csv"
    export_json.write_text(json.dumps({"cards": cards, "updated": True}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if cards:
        with export_csv.open("w", newline="", encoding="utf-8") as handle:
            keys = [
                "shot_number",
                "title",
                "song_section",
                "timecode_start",
                "timecode_end",
                "status",
                "version",
                "recommended_renderer",
                "identity_risk",
                "body_motion_risk",
            ]
            writer = csv.DictWriter(handle, fieldnames=keys)
            writer.writeheader()
            for card in cards:
                writer.writerow({key: card.get(key, "") for key in keys})


def export_captions() -> None:
    CAPTION_ROOT.mkdir(parents=True, exist_ok=True)
    rows = list_caption_lines_without_seed()
    (CAPTION_ROOT / "BURMESE_CAPTION_WORKSPACE.json").write_text(json.dumps({"lines": rows}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (CAPTION_ROOT / "BURMESE_CAPTION_WORKSPACE.csv").open("w", newline="", encoding="utf-8") as handle:
        if rows:
            keys = ["line_index", "original_text", "normalized_unicode", "pronunciation_helper", "caption_text", "start_time", "end_time", "status"]
            writer = csv.DictWriter(handle, fieldnames=keys)
            writer.writeheader()
            for row in rows:
                writer.writerow({key: row.get(key, "") for key in keys})


def list_caption_lines_without_seed() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM burmese_caption_lines ORDER BY line_index").fetchall()
    return [dict(row) for row in rows]


def sync_if_empty() -> None:
    with connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM storyboard_cards").fetchone()[0]
    if not count:
        sync_workspace_from_latest_plan()


def _record_run(state: dict[str, Any]) -> int:
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO director_runs
                (idea, project_path, output_path, storyboard_count, shot_count,
                 no_api_calls, no_uploads, no_generation)
            VALUES (?, ?, ?, ?, ?, 1, 1, 1)
            """,
            (
                state.get("idea", ""),
                state.get("project_path", str(REPO_ROOT)),
                str(LATEST_PLAN),
                int(state.get("storyboard_count", 0)),
                int(state.get("shot_count", 0)),
            ),
        )
        return int(cursor.lastrowid)


def renderer_strategy_for_shot(shot: dict[str, Any]) -> dict[str, Any]:
    source = shot.get("source_or_missing_shot_id", "")
    if "F01" in source:
        return {
            "best_renderer": "Seedance",
            "fallback_renderer": "Kling Motion Control after character_start_frame",
            "local_alternative": "raster previs + local motion rehearsal; no final video locally yet",
            "required_inputs": ["A1/A2 identity", "wardrobe/body", "bar/stage", "Burmese art", "approved motion-reference video"],
            "privacy_risk": "high if cloud references uploaded",
            "cost_risk": "medium/high until exact renderer pricing approved",
        }
    if "F06" in source:
        return {
            "best_renderer": "Kling Motion Control",
            "fallback_renderer": "Seedance",
            "local_alternative": "existing D06 trim + raster previs",
            "required_inputs": ["character_start_frame", "motion video", "A1/A2 identity guidance"],
            "privacy_risk": "high if cloud references uploaded",
            "cost_risk": "medium/high",
        }
    if source.startswith("A"):
        return {
            "best_renderer": "existing footage",
            "fallback_renderer": "local raster previs",
            "local_alternative": "use selected Batch A",
            "required_inputs": ["none"],
            "privacy_risk": "low",
            "cost_risk": "none",
        }
    return {
        "best_renderer": shot.get("recommended_renderer", "manual/local"),
        "fallback_renderer": shot.get("fallback_renderer", "existing footage"),
        "local_alternative": "raster previs and selected existing clips",
        "required_inputs": ["approved references", "shot-specific motion brief"],
        "privacy_risk": "medium/high if cloud",
        "cost_risk": "unknown until approval",
    }


def write_previs_png(path: Path, shot: dict[str, Any]) -> None:
    width, height = 1280, 720
    pixels = bytearray()
    title_hash = sum(ord(ch) for ch in shot.get("title", ""))
    dress_x = 420 + (title_hash % 360)
    for y in range(height):
        row = bytearray()
        for x in range(width):
            r = 14 + int(18 * y / height)
            g = 15 + int(12 * x / width)
            b = 16 + int(22 * (1 - y / height))
            if 760 < x < 1040 and 90 < y < 430:
                b += 32
                g += 20
            if 90 < x < 700 and 120 < y < 480:
                r += 20
                g += 8
            dx = x - dress_x
            dy = y - 390
            if dx * dx / 6400 + dy * dy / 21025 < 1:
                r, g, b = 126, 30, 25
            if abs(y - (590 - 0.035 * x)) < 3:
                r, g, b = 184, 111, 42
            row.extend((min(r, 255), min(g, 255), min(b, 255)))
        pixels.extend(b"\x00" + row)
    raw_png(path, width, height, bytes(pixels))


def raw_png(path: Path, width: int, height: int, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(data, 6))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)


def animatic_html(cards: list[dict[str, Any]]) -> str:
    slides = []
    for index, card in enumerate(cards):
        display = "block" if index == 0 else "none"
        slides.append(
            f"""<section class="slide" style="display:{display}" data-duration="{max(tc_duration(card['timecode_start'], card['timecode_end']), 2)}">
<img src="../../previs/latest/{card['shot_number']}.png" alt="{card['shot_number']}">
<div><h2>{card['shot_number']} · {card['title']}</h2><p>{card['timecode_start']} - {card['timecode_end']} · {card['song_section']}</p><p>{card['purpose']}</p></div>
</section>"""
        )
    return """<!doctype html><html><head><meta charset="utf-8"><title>Director OS Animatic</title>
<style>body{margin:0;background:#08090a;color:#f2eee8;font-family:system-ui}.slide{height:100vh;position:relative}.slide img{width:100%;height:100%;object-fit:cover}.slide div{position:absolute;left:32px;bottom:28px;max-width:720px;background:rgba(8,9,10,.72);padding:18px;border:1px solid #34302c}button{position:fixed;top:20px;right:20px;z-index:3;padding:10px 14px}</style>
</head><body><button onclick="toggle()">Play/Pause</button>""" + "\n".join(slides) + """<script>
let i=0, playing=false, timer=null; const slides=[...document.querySelectorAll('.slide')];
function show(n){slides[i].style.display='none'; i=(n+slides.length)%slides.length; slides[i].style.display='block';}
function step(){show(i+1); if(playing) timer=setTimeout(step, Number(slides[i].dataset.duration)*1000);}
function toggle(){playing=!playing; if(playing) timer=setTimeout(step, Number(slides[i].dataset.duration)*1000); else clearTimeout(timer);}
</script></body></html>"""


def conservative_burmese_normalize(text: str) -> str:
    return text.replace("\ufeff", "").strip()


def tc_duration(start: str, end: str) -> float:
    return max(tc_seconds(end) - tc_seconds(start), 0)


def tc_seconds(value: str) -> float:
    try:
        minutes, seconds = value.split(":")
        return int(minutes) * 60 + float(seconds)
    except Exception:
        return 0.0
