from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote_plus, urlparse
from urllib.request import Request, urlopen

from app.config import ENGINE_ROOT, REPO_ROOT
from app.intelligence.context_builder import build_stage_context
from app.intelligence.provider_health import active_provider, provider_status
from app.intelligence.schemas import STAGES
from app.services.audit_service import write_audit
from app.services.autonomous_director_service import DEFAULT_IDEA, LATEST_PLAN, run_autonomous_director
from app.services.blocker_service import grouped_blockers, readiness_from_blockers
from app.services.db import connect, initialize_database
from app.services.director_workspace_service import (
    ANIMATIC_ROOT,
    PREVIS_ROOT,
    build_animatic,
    list_storyboard_cards,
    sync_workspace_from_latest_plan,
    write_previs_png,
)
from app.system_tools.ffmpeg_service import ffmpeg_path, probe_media, run_ffmpeg
from app.system_tools.binary_discovery import discover_binary


V09_ROOT = ENGINE_ROOT / "runs"


def create_autonomous_run(idea: str, project_path: str = str(REPO_ROOT)) -> int:
    initialize_database()
    idea = idea.strip() or DEFAULT_IDEA
    provider = active_provider()
    output_dir = V09_ROOT / datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)
    health = provider.health()
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO autonomous_runs
                (idea, project_path, status, current_stage, active_provider,
                 provider_version, output_dir)
            VALUES (?, ?, 'queued', ?, ?, ?, ?)
            """,
            (idea, project_path, STAGES[0], provider.name, health.get("version", ""), str(output_dir)),
        )
        run_id = int(cursor.lastrowid)
        for stage in STAGES:
            conn.execute(
                "INSERT INTO autonomous_run_stages (run_id, stage_name, status) VALUES (?, ?, 'pending')",
                (run_id, stage),
            )
        conn.execute(
            "INSERT INTO autonomous_run_events (run_id, event_type, message) VALUES (?, 'created', ?)",
            (run_id, "Autonomous Director OS run created."),
        )
    return run_id


def run_autonomous_studio(run_id: int, use_provider: bool = True, timeout: int = 90) -> dict[str, Any]:
    run = get_run(run_id)
    if not run:
        raise ValueError("Unknown run.")
    _update_run(run_id, status="running")
    run_autonomous_director(run["idea"], run["project_path"], dry_run=True)
    sync_workspace_from_latest_plan()
    provider = active_provider()
    blockers: list[str] = []
    for stage in STAGES:
        if get_run(run_id)["status"] in {"cancelled", "paused"}:
            break
        _stage_started(run_id, stage)
        try:
            if use_provider:
                context = build_stage_context(run["project_path"], run["idea"], stage)
                try:
                    response = provider.complete_stage(stage, context, timeout=timeout)
                except Exception as first_exc:
                    _event(run_id, "stage_retry", f"Retrying {stage} after provider failure: {first_exc}", stage)
                    try:
                        response = provider.complete_stage(stage, context, timeout=timeout)
                    except Exception as second_exc:
                        _event(run_id, "stage_fallback", f"Falling back for {stage} after retry failure: {second_exc}", stage)
                        stage_data = local_stage_output(stage, run)
                        fallback_blockers = [f"PROVIDER_FALLBACK_USED:{stage}"]
                        if "usage limit" in str(second_exc).lower():
                            fallback_blockers.append("CODEX_PROVIDER_USAGE_LIMIT")
                        stage_data["blockers"] = list(stage_data.get("blockers", [])) + fallback_blockers
                        provider_name = "local_fallback_after_provider_failure"
                        provider_version = "0.9.1"
                    else:
                        stage_data = response.data
                        _write_provider_logs(run_id, stage, response.stdout, response.stderr)
                        provider_name = response.provider_name
                        provider_version = response.provider_version
                else:
                    stage_data = response.data
                    _write_provider_logs(run_id, stage, response.stdout, response.stderr)
                    provider_name = response.provider_name
                    provider_version = response.provider_version
            else:
                stage_data = local_stage_output(stage, run)
                provider_name = "local_stage_engine"
                provider_version = "0.9"
            artifacts = execute_stage_side_effects(run_id, stage, stage_data)
            stage_artifacts = normalize_text_list(stage_data.get("artifacts", []))
            merged_artifacts = list(dict.fromkeys(stage_artifacts + artifacts))
            stage_blockers = normalize_text_list(stage_data.get("blockers", []))
            blockers.extend(stage_blockers)
            _stage_completed(run_id, stage, stage_data, provider_name, provider_version, merged_artifacts, stage_blockers)
        except Exception as exc:
            _stage_failed(run_id, stage, str(exc))
            blockers.append(f"{stage}: {exc}")
            break
    final_blockers = consolidate_blockers(blockers)
    status = readiness_from_blockers(final_blockers)
    _update_run(run_id, status=status, blockers=final_blockers, current_stage="ready_for_review")
    write_audit(
        "autonomous_studio_run",
        "autonomous_runs",
        str(run_id),
        f"v0.9 autonomous studio run completed with status {status}.",
        {"blockers": final_blockers},
    )
    return run_status(run_id)


def local_stage_output(stage: str, run: dict[str, Any]) -> dict[str, Any]:
    return {
        "stage": stage,
        "summary": f"Local stage engine completed {stage} using existing project state and v0.8 workspace.",
        "confidence": 0.68,
        "sources": [{"source": "director-os/state and director-os/plans/latest", "confidence": 0.8}],
        "artifacts": [],
        "blockers": [],
        "data": {"run_id": run["run_id"], "stage": stage},
    }


def normalize_text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for item in value:
        if isinstance(item, str):
            text = item.strip()
        else:
            text = json.dumps(item, ensure_ascii=False, sort_keys=True)
        if text:
            normalized.append(text)
    return normalized


def execute_stage_side_effects(run_id: int, stage: str, data: dict[str, Any]) -> list[str]:
    artifacts: list[str] = []
    if stage == "project_archaeology":
        artifacts.extend(update_production_state())
    if stage == "public_research":
        artifacts.extend(run_public_research(run_id))
    if stage in {"composition_and_blocking", "lighting_and_cinematography", "storyboard_generation"}:
        artifacts.extend(populate_visual_grammar())
    if stage == "storyboard_generation":
        artifacts.extend(generate_previs_options())
    if stage == "movement_direction":
        artifacts.append(write_movement_briefs())
    if stage == "caption_and_voice_plan":
        artifacts.extend(export_caption_formats())
        artifacts.append(write_voice_provider_status())
    if stage == "edit_and_animatic":
        artifacts.extend(build_edit_handoff(run_id))
    if stage == "renderer_strategy":
        artifacts.append(str(LATEST_PLAN / "RENDERER_PLAN.md"))
    if stage == "production_preparation":
        artifacts.append(write_production_control_bridge(run_id))
    return artifacts


def run_public_research(run_id: int) -> list[str]:
    queries = [
        "emotionally restrained female performance music video",
        "intimate bar cinematography warm practical cold window",
        "lateral performer movement music video profile wide shot",
        "Burmese lacquer textile craft visual reference",
        "mature blues jazz editing rhythm music video",
    ]
    sources = [
        ("Shot.Cafe", "https://shot.cafe/search/{q}", "composition"),
        ("YouTube", "https://www.youtube.com/results?search_query={q}", "movement"),
        ("Vimeo", "https://vimeo.com/search?q={q}", "movement"),
        ("FilmGrab", "https://film-grab.com/?s={q}", "cinematography"),
    ]
    with connect() as conn:
        for query in queries:
            for source, template, category in sources:
                url = template.format(q=quote_plus(query))
                status = verify_url(url)
                verification_status = research_verification_status(url, status)
                source_domain = urlparse(url).netloc
                conn.execute(
                    """
                    INSERT INTO research_items
                        (query, title, url, category, notes, rights_status, shot_pack_id,
                         verification_status, source_domain, retrieval_date, what_not_to_copy)
                    VALUES (?, ?, ?, ?, ?, 'link_only_do_not_copy', 'F01_side_travel_dance',
                            ?, ?, ?, ?)
                    """,
                    (
                        query,
                        f"{source}: {query}",
                        url,
                        category,
                        f"Verified status: {status}. Store notes/timecodes only; do not copy/rehost media.",
                        verification_status,
                        source_domain,
                        datetime.now(timezone.utc).date().isoformat(),
                        "Do not copy, scrape, download, or rehost copyrighted media. Store links, notes, tags, timecodes, and user-owned/licensed uploads only.",
                    ),
                )
    path = V09_ROOT / str(run_id) / "RESEARCH_SOURCES.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        rows = [dict(row) for row in conn.execute("SELECT * FROM research_items ORDER BY item_id DESC LIMIT 40").fetchall()]
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return [str(path)]


def verify_url(url: str) -> str:
    if os.environ.get("DIRECTOR_OS_DISABLE_NETWORK") == "1":
        return "network_disabled"
    try:
        request = Request(url, method="GET", headers={"User-Agent": "DirectorOS/0.9 link verifier"})
        with urlopen(request, timeout=8) as response:
            return str(response.status)
    except Exception as exc:
        return f"unverified:{type(exc).__name__}"


def research_verification_status(url: str, status: str) -> str:
    if "search" in urlparse(url).path or "search_query=" in url or "?s=" in url or "results?" in url:
        return "search_suggestion_only"
    if status == "200":
        return "verified"
    if status.startswith("unverified:"):
        return "unavailable"
    if status == "network_disabled":
        return "reachable_but_metadata_limited"
    return "rights_unknown"


def populate_visual_grammar() -> list[str]:
    cards = list_storyboard_cards()
    diagram_root = ENGINE_ROOT / "diagrams" / "latest"
    diagram_root.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        for card in cards:
            composition = {
                "balance": "asymmetric",
                "performer_position": "right_third" if "Side" in card["title"] else "center_or_right_third",
                "negative_space": "left_winter_window",
                "foreground": "out_of_focus_empty_glass_or_rose",
                "midground": "performer",
                "background": "amber_bar_shelves",
                "background_people": "none",
                "visual_intent": "isolation",
            }
            camera = {
                "lens_intent": "moderate_wide",
                "height": "waist_to_chest",
                "angle": "level",
                "distance": card["framing"],
                "movement": card["camera_movement"],
                "screen_direction": "left_to_right",
            }
            lighting = {
                "key": "soft_warm_side_key",
                "fill": "restrained_cool_window_fill",
                "rim": "subtle_crimson_edge",
                "practicals": "amber_bar_lamps",
                "face_exposure": "partial_controlled",
                "contrast": "high",
                "motivation": "bar_practicals_and_winter_window",
            }
            blocking = {
                "start_mark": "bar_floor_left_or_center",
                "end_mark": "bar_floor_right_or_window_edge",
                "travel_direction": "left_to_right",
                "body_orientation": "profile_threequarter",
                "eyeline": "past camera or toward winter window",
                "arm_level": "below_shoulder",
                "prop_relationship": "objects foreground, microphone withheld",
                "camera_relationship": "camera tracks beside performer",
                "background_action": "none",
            }
            diagram = diagram_root / f"{card['shot_number']}_diagram.svg"
            diagram.write_text(blocking_diagram_svg(card["shot_number"]), encoding="utf-8")
            conn.execute(
                """
                INSERT INTO visual_grammar
                    (shot_number, composition, camera, lighting, blocking, diagram_path)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(shot_number) DO UPDATE SET
                    composition = excluded.composition,
                    camera = excluded.camera,
                    lighting = excluded.lighting,
                    blocking = excluded.blocking,
                    diagram_path = excluded.diagram_path,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    card["shot_number"],
                    json.dumps(composition),
                    json.dumps(camera),
                    json.dumps(lighting),
                    json.dumps(blocking),
                    str(diagram),
                ),
            )
    return [str(diagram_root)]


def generate_previs_options() -> list[str]:
    cards = list_storyboard_cards()
    option_root = ENGINE_ROOT / "previs-options" / "latest"
    option_root.mkdir(parents=True, exist_ok=True)
    count = 0
    for card in cards[:6]:
        for variant in ["composition", "lighting", "environment"]:
            path = option_root / f"{card['shot_number']}_{variant}.png"
            shot = {
                "title": f"{card['title']} {variant}",
                "shot_number": card["shot_number"],
            }
            write_previs_png(path, shot)
            count += 1
    manifest = option_root / "ORIGIN_MANIFEST.json"
    manifest.write_text(
        json.dumps(
            {
                "origin": "ASSET COMPOSITE PREVIS",
                "ai_generated_count": 0,
                "composite_count": count,
                "blocker": "LOCAL STORYBOARD MODEL REQUIRED",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return [str(option_root), str(manifest)]


def write_movement_briefs() -> str:
    cards = list_storyboard_cards()
    path = LATEST_PLAN / "PHONE_RECORDABLE_MOVEMENT_BRIEFS.md"
    lines = ["# Phone-Recordable Movement Briefs", ""]
    for card in cards:
        if "high" in card["body_motion_risk"].lower() or "Side" in card["title"] or "Chorus" in card["title"]:
            lines.extend(
                [
                    f"## {card['shot_number']} {card['title']}",
                    "",
                    "- three grounded lateral steps",
                    "- left-right-left weight transfer",
                    "- arms below shoulder level",
                    "- restrained wrist release",
                    "- shoulder response on the beat",
                    "- lifted but natural torso",
                    "- one brief three-quarter head turn",
                    "- camera: phone at waist-to-chest height, medium-wide/full-body",
                    "- floor marks: start and end visible; preserve lateral displacement",
                    "- do not transfer source identity, clothing, location or body shape",
                    "- hard no: kick, fighting shape, random spin, K-pop/TikTok, fake hips/body",
                    "",
                ]
            )
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def export_caption_formats() -> list[str]:
    rows = caption_rows()
    caption_dir = ENGINE_ROOT / "captions" / "latest"
    caption_dir.mkdir(parents=True, exist_ok=True)
    srt = caption_dir / "CAPTIONS.srt"
    vtt = caption_dir / "CAPTIONS.vtt"
    ass = caption_dir / "CAPTIONS.ass"
    srt.write_text(render_srt(rows), encoding="utf-8")
    vtt.write_text("WEBVTT\n\n" + render_vtt_rows(rows), encoding="utf-8")
    ass.write_text(render_ass(rows), encoding="utf-8")
    return [str(srt), str(vtt), str(ass)]


def write_voice_provider_status() -> str:
    path = ENGINE_ROOT / "voice" / "VOICE_PROVIDER_STATUS.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "system_voice": {"available": bool(shutil.which("say")), "status": "local_system_candidate"},
        "azure": {"available": bool(os.environ.get("AZURE_SPEECH_KEY")), "status": "requires_explicit_cloud_approval"},
        "local_burmese": {"available": False, "status": "LOCAL_VOICE_MODEL_REQUIRED"},
        "operational": False,
        "blocker": "VOICE_PROVIDER_NOT_CONFIGURED",
    }
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return str(path)


def build_edit_handoff(run_id: int) -> list[str]:
    cards = list_storyboard_cards()
    run_dir = ENGINE_ROOT / "animatics" / str(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    artifacts = []
    artifacts.append(write_shot_list(run_dir, cards))
    artifacts.append(write_edl(run_dir, cards))
    artifacts.append(write_otio_placeholder(run_dir, cards))
    artifacts.append(write_davinci_xml(run_dir, cards))
    artifacts.extend(export_caption_formats())
    artifacts.append(write_edit_decisions(run_dir, cards))
    html = build_animatic(run_id)
    artifacts.append(html["path"])
    artifacts.extend(build_mp4_animatics(run_id, run_dir, cards))
    return artifacts


def build_mp4_animatics(run_id: int, run_dir: Path, cards: list[dict[str, Any]]) -> list[str]:
    artifacts: list[str] = []
    log_path = run_dir / "BUILD_LOG.txt"
    command_log = run_dir / "FFMPEG_COMMAND.json"
    metadata_path = run_dir / "MEDIA_METADATA.json"
    ffmpeg = find_ffmpeg()
    log_path.write_text("", encoding="utf-8")
    if not ffmpeg:
        log_path.write_text("FFMPEG_REQUIRED_FOR_MP4_ANIMATIC\n", encoding="utf-8")
        record_backend_status("ffmpeg_mp4_animatic", "blocked", {"ffmpeg": None}, "FFMPEG_REQUIRED_FOR_MP4_ANIMATIC")
        return [str(log_path)]

    image_list = run_dir / "frames.txt"
    with image_list.open("w", encoding="utf-8") as handle:
        for card in cards:
            handle.write(f"file '{Path(card['raster_path']).resolve()}'\n")
            handle.write(f"duration {max(tc_duration(card['timecode_start'], card['timecode_end']), 2)}\n")
        if cards:
            handle.write(f"file '{Path(cards[-1]['raster_path']).resolve()}'\n")

    audio = REPO_ROOT / "audio" / "01.mp3"
    clean = run_dir / "ANIMATIC.mp4"
    captioned = run_dir / "ANIMATIC_WITH_CAPTIONS.mp4"
    review = run_dir / "ANIMATIC_REVIEW.mp4"
    commands: dict[str, list[str]] = {}

    base_args = ["-y", "-f", "concat", "-safe", "0", "-i", str(image_list)]
    if audio.exists():
        base_args.extend(["-i", str(audio), "-shortest"])
    base_args.extend(["-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20"])
    if audio.exists():
        base_args.extend(["-c:a", "aac", "-b:a", "192k"])
    base_args.append(str(clean))
    commands["clean"] = [ffmpeg, *base_args]
    result = run_ffmpeg(base_args, log_path)
    if result.returncode == 0 and clean.exists():
        artifacts.append(str(clean))

    captions = ENGINE_ROOT / "captions" / "latest" / "CAPTIONS.ass"
    if clean.exists() and captions.exists():
        caption_args = ["-y", "-i", str(clean), "-vf", f"subtitles={escape_filter_path(captions)}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "copy", str(captioned)]
        commands["captioned"] = [ffmpeg, *caption_args]
        cap_result = run_ffmpeg(caption_args, log_path)
        if cap_result.returncode == 0 and captioned.exists():
            artifacts.append(str(captioned))
        else:
            with log_path.open("a", encoding="utf-8") as log:
                log.write("Caption burn unavailable; keeping separate SRT/VTT/ASS files.\n")

    if clean.exists():
        review_args = [
            "-y",
            "-i",
            str(clean),
            "-vf",
            "drawtext=text='DIRECTOR OS REVIEW ANIMATIC':x=40:y=40:fontsize=38:fontcolor=white:box=1:boxcolor=black@0.5",
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
        commands["review"] = [ffmpeg, *review_args]
        rev_result = run_ffmpeg(review_args, log_path)
        if rev_result.returncode == 0 and review.exists():
            artifacts.append(str(review))

    command_log.write_text(json.dumps(commands, indent=2) + "\n", encoding="utf-8")
    artifacts.append(str(command_log))
    media = {}
    for name, path in {"clean": clean, "captioned": captioned, "review": review}.items():
        if path.exists():
            try:
                media[name] = probe_media(path)
            except Exception as exc:
                media[name] = {"error": str(exc)}
    metadata_path.write_text(json.dumps(media, indent=2) + "\n", encoding="utf-8")
    artifacts.extend([str(metadata_path), str(log_path)])
    record_backend_status("ffmpeg_mp4_animatic", "healthy" if clean.exists() else "failed", {"ffmpeg": ffmpeg, "metadata": media}, "" if clean.exists() else "FFMPEG_MP4_BUILD_FAILED")
    return artifacts


def write_production_control_bridge(run_id: int) -> str:
    path = LATEST_PLAN / "PRODUCTION_CONTROL_BRIDGE.json"
    data = {
        "run_id": run_id,
        "jobs": "existing v0.5+ job system remains available",
        "exports": "manual export and readiness gates remain available",
        "qc": "result import/QC/decision system remains available",
        "blocked_until_approval": ["cloud upload", "paid API", "voice cloning", "final renderer submission"],
    }
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return str(path)


def run_status(run_id: int) -> dict[str, Any]:
    run = get_run(run_id)
    if not run:
        return {}
    with connect() as conn:
        stages = [dict(row) for row in conn.execute("SELECT * FROM autonomous_run_stages WHERE run_id = ? ORDER BY stage_id", (run_id,)).fetchall()]
        events = [dict(row) for row in conn.execute("SELECT * FROM autonomous_run_events WHERE run_id = ? ORDER BY event_id DESC LIMIT 50", (run_id,)).fetchall()]
    completed = [stage for stage in stages if stage["status"] == "completed"]
    last_artifact = ""
    for stage in reversed(stages):
        artifacts = json.loads(stage["artifacts"] or "[]")
        if artifacts:
            last_artifact = artifacts[-1]
            break
    return {
        "run": run,
        "stages": stages,
        "events": events,
        "completed_stages": len(completed),
        "total_stages": len(stages),
        "last_artifact": last_artifact,
        "blockers": json.loads(run["blockers"] or "[]"),
        "blocker_groups": grouped_blockers(json.loads(run["blockers"] or "[]")),
        "decisions_required": json.loads(run["decisions_required"] or "[]"),
        "next_action": next_action_for_run(run),
        "web_url": f"http://127.0.0.1:8787/director-runs/{run_id}",
    }


def list_runs() -> list[dict[str, Any]]:
    initialize_database()
    with connect() as conn:
        rows = conn.execute("SELECT * FROM autonomous_runs ORDER BY run_id DESC").fetchall()
    return [dict(row) for row in rows]


def get_run(run_id: int) -> Optional[dict[str, Any]]:
    initialize_database()
    with connect() as conn:
        row = conn.execute("SELECT * FROM autonomous_runs WHERE run_id = ?", (run_id,)).fetchone()
    return dict(row) if row else None


def set_run_status(run_id: int, status: str) -> None:
    _update_run(run_id, status=status)
    _event(run_id, status, f"Run marked {status}.")


def retry_stage(run_id: int, stage: str) -> dict[str, Any]:
    if stage not in STAGES:
        raise ValueError("Unknown stage.")
    with connect() as conn:
        conn.execute(
            "UPDATE autonomous_run_stages SET status = 'pending', error = '', blockers = '[]' WHERE run_id = ? AND stage_name = ?",
            (run_id, stage),
        )
    _event(run_id, "retry", f"Stage retry requested: {stage}", stage)
    # Run only local side effects for retry to avoid accidental spend/long provider calls.
    data = local_stage_output(stage, get_run(run_id))
    artifacts = execute_stage_side_effects(run_id, stage, data)
    _stage_completed(run_id, stage, data, "local_retry_engine", "0.9", artifacts, [])
    return run_status(run_id)


def _update_run(run_id: int, **fields: Any) -> None:
    if not fields:
        return
    if "blockers" in fields and isinstance(fields["blockers"], list):
        fields["blockers"] = json.dumps(fields["blockers"])
    if "decisions_required" in fields and isinstance(fields["decisions_required"], list):
        fields["decisions_required"] = json.dumps(fields["decisions_required"])
    fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    assignments = ", ".join(f"{key} = ?" for key in fields)
    values = list(fields.values()) + [run_id]
    with connect() as conn:
        conn.execute(f"UPDATE autonomous_runs SET {assignments} WHERE run_id = ?", values)


def _stage_started(run_id: int, stage: str) -> None:
    _update_run(run_id, current_stage=stage)
    with connect() as conn:
        conn.execute(
            "UPDATE autonomous_run_stages SET status = 'running', started_at = ? WHERE run_id = ? AND stage_name = ?",
            (datetime.now(timezone.utc).isoformat(), run_id, stage),
        )
    _event(run_id, "stage_started", f"Started {stage}.", stage)


def _stage_completed(
    run_id: int,
    stage: str,
    data: dict[str, Any],
    provider: str,
    provider_version: str,
    artifacts: list[str],
    blockers: list[str],
) -> None:
    with connect() as conn:
        conn.execute(
            """
            UPDATE autonomous_run_stages
            SET status = 'completed', confidence = ?, provider = ?, provider_version = ?,
                summary = ?, sources = ?, artifacts = ?, blockers = ?, completed_at = ?
            WHERE run_id = ? AND stage_name = ?
            """,
            (
                float(data.get("confidence", 0)),
                provider,
                provider_version,
                data.get("summary", ""),
                json.dumps(data.get("sources", [])),
                json.dumps(artifacts),
                json.dumps(blockers),
                datetime.now(timezone.utc).isoformat(),
                run_id,
                stage,
            ),
        )
    _event(run_id, "stage_completed", f"Completed {stage}.", stage, {"artifacts": artifacts, "blockers": blockers})


def _stage_failed(run_id: int, stage: str, error: str) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE autonomous_run_stages SET status = 'failed', error = ?, completed_at = ? WHERE run_id = ? AND stage_name = ?",
            (error, datetime.now(timezone.utc).isoformat(), run_id, stage),
        )
    _event(run_id, "stage_failed", f"Failed {stage}: {error}", stage)


def _event(run_id: int, event_type: str, message: str, stage: str = "", metadata: Optional[dict[str, Any]] = None) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO autonomous_run_events (run_id, event_type, stage_name, message, metadata) VALUES (?, ?, ?, ?, ?)",
            (run_id, event_type, stage, message, json.dumps(metadata or {})),
        )


def _write_provider_logs(run_id: int, stage: str, stdout: str, stderr: str) -> None:
    run = get_run(run_id)
    if not run:
        return
    root = Path(run["output_dir"]) / "provider-logs"
    root.mkdir(parents=True, exist_ok=True)
    out = root / f"{stage}.stdout.txt"
    err = root / f"{stage}.stderr.txt"
    out.write_text(stdout, encoding="utf-8")
    err.write_text(stderr, encoding="utf-8")
    with connect() as conn:
        conn.execute(
            "UPDATE autonomous_run_stages SET stdout_path = ?, stderr_path = ? WHERE run_id = ? AND stage_name = ?",
            (str(out), str(err), run_id, stage),
        )


def update_production_state() -> list[str]:
    path = ENGINE_ROOT / "state" / "PRODUCTION_STATE.json"
    data = {
        "current_status": "v0.9 autonomous studio connected to v0.8 workspace and v0.6 production/QC engine",
        "master_audio": "audio/01.mp3",
        "current_best_cut": "production/edit/roughcut-v2/ROUGH-CUT-V2C_SAFE-LOCAL-RECUT_WITH-MP3.mp4",
        "blocked": ["LOCAL_STORYBOARD_MODEL_REQUIRED", "FFMPEG_REQUIRED_FOR_MP4_ANIMATIC", "VOICE_PROVIDER_NOT_CONFIGURED"],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tool_path = ENGINE_ROOT / "state" / "TOOL_CAPABILITIES.json"
    tool_path.write_text(json.dumps(tool_capabilities(), indent=2) + "\n", encoding="utf-8")
    return [str(path), str(tool_path)]


def tool_capabilities() -> dict[str, Any]:
    return {
        "codex": provider_status(),
        "ffmpeg": {"available": bool(find_ffmpeg()), "path": find_ffmpeg()},
        "local_ai_image": {"available": False, "status": "LOCAL_STORYBOARD_MODEL_REQUIRED"},
        "voice": {"available": bool(shutil.which("say")), "status": "system voice candidate only; Burmese quality unverified"},
    }


def consolidate_blockers(blockers: list[str]) -> list[str]:
    result = []
    if not find_ffmpeg():
        result.append("FFMPEG_REQUIRED_FOR_MP4_ANIMATIC")
    result.append("LOCAL_STORYBOARD_MODEL_REQUIRED")
    result.append("VOICE_PROVIDER_NOT_CONFIGURED")
    for blocker in blockers:
        if blocker and blocker not in result and not blocker.startswith("REAL_INTELLIGENCE_PROVIDER_NOT_USED"):
            result.append(blocker)
    return result


def next_action_for_run(run: dict[str, Any]) -> str:
    blockers = json.loads(run.get("blockers") or "[]")
    if "FFMPEG_REQUIRED_FOR_MP4_ANIMATIC" in blockers:
        return "Install or provide ffmpeg path to build MP4 animatic."
    if "LOCAL_STORYBOARD_MODEL_REQUIRED" in blockers:
        return "Review the MP4 animatic and choose whether to configure AI storyboard generation."
    return "Review storyboard and production bridge."


def blocking_diagram_svg(shot_number: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 500">
<rect width="800" height="500" fill="#101112"/>
<rect x="90" y="90" width="620" height="300" fill="#18191b" stroke="#34302c" stroke-width="4"/>
<text x="100" y="55" fill="#d69b49" font-family="Arial" font-size="28">{shot_number} Blocking Diagram</text>
<circle cx="520" cy="250" r="34" fill="#9d3b32"/><text x="475" y="320" fill="#f2eee8" font-family="Arial" font-size="18">performer</text>
<polygon points="180,260 260,220 260,300" fill="#d69b49"/><text x="140" y="335" fill="#f2eee8" font-family="Arial" font-size="18">camera</text>
<line x1="380" y1="250" x2="580" y2="250" stroke="#d69b49" stroke-width="8" marker-end="url(#arrow)"/>
<circle cx="240" cy="160" r="22" fill="#52606a"/><text x="190" y="130" fill="#afa79a" font-family="Arial" font-size="16">foreground glass</text>
<circle cx="640" cy="130" r="28" fill="#c23b32"/><text x="590" y="105" fill="#afa79a" font-family="Arial" font-size="16">rim light</text>
<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="5" refY="3" orient="auto"><path d="M0,0 L0,6 L6,3 z" fill="#d69b49"/></marker></defs>
</svg>"""


def caption_rows() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = [dict(row) for row in conn.execute("SELECT * FROM burmese_caption_lines ORDER BY line_index").fetchall()]
    if rows:
        return rows
    # Seed via v0.8 service lazily.
    from app.services.director_workspace_service import list_caption_lines

    return list_caption_lines()


def render_srt(rows: list[dict[str, Any]]) -> str:
    parts = []
    for idx, row in enumerate(rows[:80], start=1):
        start = row.get("start_time") or seconds_to_srt((idx - 1) * 4)
        end = row.get("end_time") or seconds_to_srt(idx * 4)
        parts.append(f"{idx}\n{start} --> {end}\n{row.get('caption_text') or row.get('original_text')}\n")
    return "\n".join(parts)


def render_vtt_rows(rows: list[dict[str, Any]]) -> str:
    return render_srt(rows).replace(",", ".")


def render_ass(rows: list[dict[str, Any]]) -> str:
    lines = [
        "[Script Info]",
        "Title: Director OS Burmese Captions",
        "ScriptType: v4.00+",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, Alignment",
        "Style: Default,Arial,44,&H00FFFFFF,2",
        "[Events]",
        "Format: Start, End, Style, Text",
    ]
    for idx, row in enumerate(rows[:80], start=1):
        lines.append(f"Dialogue: {seconds_to_ass((idx - 1) * 4)},{seconds_to_ass(idx * 4)},Default,{row.get('caption_text') or row.get('original_text')}")
    return "\n".join(lines) + "\n"


def write_shot_list(root: Path, cards: list[dict[str, Any]]) -> str:
    path = root / "SHOT_LIST.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["shot_number", "title", "start", "end", "renderer", "status"])
        writer.writeheader()
        for card in cards:
            writer.writerow(
                {
                    "shot_number": card["shot_number"],
                    "title": card["title"],
                    "start": card["timecode_start"],
                    "end": card["timecode_end"],
                    "renderer": card["recommended_renderer"],
                    "status": card["status"],
                }
            )
    return str(path)


def write_edl(root: Path, cards: list[dict[str, Any]]) -> str:
    path = root / "TIMELINE.edl"
    lines = ["TITLE: Director OS Animatic", "FCM: NON-DROP FRAME", ""]
    for idx, card in enumerate(cards, start=1):
        lines.append(f"{idx:03d}  AX       V     C        {card['timecode_start']} {card['timecode_end']} {card['timecode_start']} {card['timecode_end']}")
        lines.append(f"* FROM CLIP NAME: {card['shot_number']}_{card['title']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def write_otio_placeholder(root: Path, cards: list[dict[str, Any]]) -> str:
    path = root / "TIMELINE.otio"
    data = {"OTIO_SCHEMA": "Timeline.1", "name": "Director OS Animatic", "tracks": [{"children": cards}]}
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return str(path)


def write_davinci_xml(root: Path, cards: list[dict[str, Any]]) -> str:
    path = root / "DAVINCI_HANDOFF.xml"
    body = "\n".join(f"<shot id=\"{card['shot_number']}\" title=\"{card['title']}\" />" for card in cards)
    path.write_text(f"<?xml version=\"1.0\" encoding=\"UTF-8\"?><director_os>{body}</director_os>\n", encoding="utf-8")
    return str(path)


def write_edit_decisions(root: Path, cards: list[dict[str, Any]]) -> str:
    path = root / "EDIT_DECISIONS.json"
    path.write_text(json.dumps({"shots": cards}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return str(path)


def find_ffmpeg() -> Optional[str]:
    return discover_binary("ffmpeg")


def escape_filter_path(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def record_backend_status(name: str, status: str, health: dict[str, Any], blocker: str) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO local_backend_status (backend_name, status, health, blocker)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(backend_name) DO UPDATE SET
                status = excluded.status,
                health = excluded.health,
                blocker = excluded.blocker,
                updated_at = CURRENT_TIMESTAMP
            """,
            (name, status, json.dumps(health), blocker),
        )


def seconds_to_srt(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    sec = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{sec:06.3f}".replace(".", ",")


def seconds_to_ass(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    sec = seconds % 60
    return f"{hours}:{minutes:02d}:{sec:05.2f}"


def tc_duration(start: str, end: str) -> float:
    return max(tc_seconds(end) - tc_seconds(start), 0)


def tc_seconds(value: str) -> float:
    try:
        minutes, seconds = value.split(":")
        return int(minutes) * 60 + float(seconds)
    except Exception:
        return 0.0
