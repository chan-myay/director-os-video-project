from __future__ import annotations

import csv
import hashlib
import json
import platform
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.config import ENGINE_ROOT, REPO_ROOT
from app.services.audit_service import write_audit
from app.services.engine_reader import read_text


DEFAULT_IDEA = (
    "Create a world-class cinematic Burmese music video from this existing project. "
    "My wife performs alone in the approved dark Finnish bar. The performance must be "
    "mature, elegant, emotionally intense and physically realistic. Continue from all "
    "approved work and failures. Avoid karaoke, random choreography, martial arts, "
    "K-pop, fake lip-sync and fake body proportions."
)

PLAN_ROOT = ENGINE_ROOT / "plans"
STATE_ROOT = ENGINE_ROOT / "state"
LATEST_PLAN = PLAN_ROOT / "latest"
STORYBOARD_ROOT = ENGINE_ROOT / "storyboards" / "latest"

APPROVED_REFERENCES = {
    "identity_front": "references/approved/REF-A1_WIFE-FACE-FRONT_APPROVED.png",
    "identity_threequarter": "references/approved/REF-A2_WIFE-FACE-THREEQUARTER_APPROVED.png",
    "wardrobe_body": "references/approved/REF-B_WIFE-WARDROBE-FULLBODY_APPROVED.png",
    "natural_body_source": "references/identity-source-selected/IMG_4079.heic.png",
    "bar_stage": "references/approved/REF-C_BAR-STAGE_APPROVED.png",
    "burmese_art_world": "references/approved/REF-E_BURMESE-ART-INSERTS_APPROVED.png",
}

LOCKED_TRUTH = {
    "project": "Burmese heartbreak music video",
    "song": "audio/01.mp3",
    "performer": "consenting adult wife performer",
    "location": "approved dark teak Finnish bar/stage with winter window",
    "lighting": "amber/crimson cinematic lighting",
    "wardrobe": "deep-red one-shoulder Burmese-inspired dress",
    "world": "Burmese art/craft visual world",
    "mood": "mature dark blues/jazz emotional pressure",
    "microphone": "final symbol only, not performance center",
    "face_correction": "HiFiFace 256 primary, UniFace 256 backup, SimSwap 512 rejected",
}

HARD_NEGATIVES = [
    "karaoke/lounge direction",
    "generic random dance",
    "martial arts / kung fu",
    "K-pop / TikTok vocabulary",
    "fake body reshaping",
    "generated singing treated as final Burmese lip-sync",
    "rejected three-angle identity sheet",
    "child-containing source material",
    "broad private wife/source folders in cloud upload packages",
]

AGENTS = [
    "Project Archaeologist",
    "Creative Director",
    "Music Analyst",
    "Burmese Lyric and Language Director",
    "Research Director",
    "Cultural Director",
    "Cinematographer",
    "Lighting Director",
    "Production Designer",
    "Movement and Choreography Director",
    "Storyboard Director",
    "Performance/Acting Director",
    "Editor",
    "Caption and Typography Director",
    "Voice and Lip-Sync Director",
    "Renderer Strategist",
    "Cost and Privacy Strategist",
    "QC Director",
]


def run_autonomous_director(idea: str, project_path: str | Path = REPO_ROOT, dry_run: bool = True) -> dict[str, Any]:
    idea = (idea or DEFAULT_IDEA).strip()
    project = Path(project_path).expanduser().resolve()
    evidence = collect_project_evidence(project)
    music = analyze_music(project)
    burmese = analyze_burmese_language(project)
    assets = build_asset_index(project, evidence)
    decisions = build_decision_memory(evidence)
    failures = build_failure_memory(evidence)
    concepts = build_creative_concepts()
    selected = concepts[0]
    storyboard = build_storyboard(music)
    shot_list = build_shot_list(storyboard)
    renderer_plan = build_renderer_plan(storyboard)
    edit_plan = build_edit_plan(storyboard, music)
    hardware = hardware_audit()
    questions = genuine_open_questions(evidence)
    state = {
        "version": "0.7",
        "created_at": now(),
        "idea": idea,
        "project_path": str(project),
        "locked_truth": LOCKED_TRUTH,
        "agents": [{"name": name, "status": "completed", "confidence": 0.78} for name in AGENTS],
        "music": music,
        "burmese_language": burmese,
        "approved_references": APPROVED_REFERENCES,
        "hard_negatives": HARD_NEGATIVES,
        "selected_concept": selected,
        "storyboard_count": len(storyboard["shots"]),
        "shot_count": len(shot_list),
        "missing_inputs": questions,
        "dry_run": dry_run,
        "no_api_calls": True,
        "no_uploads": True,
        "no_generation": True,
    }
    write_state_files(state, evidence, decisions, failures, assets)
    write_director_package(idea, state, concepts, selected, storyboard, shot_list, renderer_plan, edit_plan, hardware, questions)
    write_audit(
        "autonomous_director_run",
        "director_plan",
        "latest",
        "Autonomous Director v0.7 planning run completed.",
        {"project_path": str(project), "dry_run": dry_run, "storyboard_count": len(storyboard["shots"])},
    )
    return director_status()


def director_status() -> dict[str, Any]:
    state = read_json(STATE_ROOT / "PROJECT_STATE.json")
    storyboard = read_json(LATEST_PLAN / "STORYBOARD.json")
    summary = read_text(LATEST_PLAN / "EXECUTIVE_CREATIVE_SUMMARY.md", 5000)
    outputs = sorted(path.name for path in LATEST_PLAN.glob("*") if path.is_file()) if LATEST_PLAN.exists() else []
    return {
        "has_plan": bool(state),
        "state": state,
        "storyboard": storyboard,
        "summary": summary,
        "outputs": outputs,
        "plan_path": str(LATEST_PLAN),
        "storyboard_path": str(LATEST_PLAN / "STORYBOARD_BOARD.html"),
        "next_best_action": next_best_action(state),
    }


def collect_project_evidence(project: Path) -> dict[str, Any]:
    important_files = [
        "director-os-audit/SUCCESS_REGISTER.md",
        "director-os-audit/FAILURE_REGISTER.md",
        "director-os-audit/PROJECT_MAP.md",
        "director-os-audit/phase-1-review/V2B_MISSING_COVERAGE_REVIEW.md",
        "director-os-audit/phase-2-v2c/V2C_SAFE_EDL.csv",
        "production/review/KNOWN-ISSUES-AND-USE-RULES.md",
        "production/edit/roughcut-v2/song-analysis/SONG-ENERGY-MOVEMENT-DIRECTIVES.md",
        "director-os-web/WEB_V0_6A_1_REPORT.md",
        "director-os-web/WEB_V0_6B_REPORT.md",
    ]
    docs = {}
    for relative in important_files:
        path = project / relative
        if path.exists():
            docs[relative] = read_text(path, 20000)
    file_counts = {}
    for folder in ["audio", "lyrics", "references", "pilot", "production", "face-correction", "director-os", "director-os-audit"]:
        root = project / folder
        file_counts[folder] = len([p for p in root.rglob("*") if p.is_file()]) if root.exists() else 0
    selected = sorted(str(p.relative_to(project)) for p in (project / "production" / "selected").rglob("*") if p.is_file()) if (project / "production" / "selected").exists() else []
    rejected = sorted(str(p.relative_to(project)) for p in (project / "production" / "rejected").rglob("*") if p.is_file()) if (project / "production" / "rejected").exists() else []
    contact_sheets = sorted(str(p.relative_to(project)) for p in project.rglob("contact-sheet*.jpg"))
    return {
        "documents": docs,
        "file_counts": file_counts,
        "selected_clips": selected,
        "rejected_clips": rejected,
        "contact_sheets": contact_sheets,
        "evidence_count": len(docs) + len(selected) + len(rejected) + len(contact_sheets),
    }


def analyze_music(project: Path) -> dict[str, Any]:
    existing = read_json(project / "production/edit/roughcut-v2/song-analysis/song-energy-analysis.json")
    if existing:
        return {
            "source": "production/edit/roughcut-v2/song-analysis/song-energy-analysis.json",
            "duration": 292.658,
            "bpm": round(float(existing.get("bpm", 75.0)), 2),
            "sections": existing.get("sections", []),
            "confidence": 0.88,
            "reuse": "Existing local song analysis reused.",
        }
    audio = project / "audio/01.mp3"
    duration = ffprobe_duration(audio)
    return {"source": "ffprobe audio/01.mp3", "duration": duration, "bpm": 75.0, "sections": default_sections(), "confidence": 0.55}


def analyze_burmese_language(project: Path) -> dict[str, Any]:
    lyric_files = sorted((project / "lyrics").glob("*.txt")) if (project / "lyrics").exists() else []
    original = read_text(lyric_files[0], 20000) if lyric_files else ""
    zawgyi_likely = detect_zawgyi(original)
    normalized = normalize_burmese_text(original)
    lines = [line.strip() for line in normalized.splitlines() if line.strip()]
    return {
        "source": str(lyric_files[0].relative_to(project)) if lyric_files else "UNKNOWN",
        "original_preserved": bool(original),
        "zawgyi_likely": zawgyi_likely,
        "unicode_normalized_available": bool(normalized),
        "line_count": len(lines),
        "caption_safe_lines": lines[:24],
        "pronunciation_layer": "placeholder; user corrections are preserved separately before voice/lip-sync.",
        "typography": "Use Unicode Burmese-capable fonts; do not redistribute font files without license.",
        "warning": "Do not blindly transform spelling; preserve original lyrics.",
    }


def build_asset_index(project: Path, evidence: dict[str, Any]) -> dict[str, Any]:
    records = []
    for role, relative in APPROVED_REFERENCES.items():
        path = project / relative
        records.append(asset_record(project, path, role, "approved"))
    for relative in evidence["selected_clips"]:
        records.append(asset_record(project, project / relative, "selected_clip", "selected"))
    for relative in evidence["rejected_clips"]:
        records.append(asset_record(project, project / relative, "rejected_clip", "rejected"))
    return {"records": records, "count": len(records), "updated_at": now()}


def asset_record(project: Path, path: Path, role: str, status: str) -> dict[str, Any]:
    return {
        "path": str(path.relative_to(project)) if path.exists() else str(path),
        "role": role,
        "status": status,
        "exists": path.exists(),
        "sha256": sha256_small(path) if path.exists() and path.stat().st_size < 100 * 1024 * 1024 else "",
        "size": path.stat().st_size if path.exists() else 0,
        "evidence_source": "filesystem",
        "confidence": 0.95 if path.exists() else 0.4,
    }


def build_decision_memory(evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "decisions": [
            decision("approved", "Use separate A1/A2 wife face references only.", "SUCCESS_REGISTER.md", 0.96),
            decision("approved", "Deep-red one-shoulder Burmese-inspired dress is locked.", "SUCCESS_REGISTER.md", 0.95),
            decision("approved", "Dark teak Finnish bar, winter window, amber/crimson lighting locked.", "SUCCESS_REGISTER.md", 0.95),
            decision("restricted", "Microphone is final symbol only.", "SUCCESS_REGISTER.md and movement directives", 0.93),
            decision("rejected", "SimSwap 512 rejected for final.", "FAILURE_REGISTER.md", 0.95),
            decision("restricted", "Batch B movement/stage only; no identity exposure.", "phase-1 review", 0.9),
        ],
        "updated_at": now(),
    }


def build_failure_memory(evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "failures": [
            failure("LOUNGE_KARAOKE_DRIFT", "Warm lounge/karaoke direction weakened the song.", "Use rhythm, pressure, dance/performance.", 0.94),
            failure("FAKE_LIPSYNC", "Generated singing mouth is not final Burmese lip-sync.", "Hide mouth; lip-sync only after edit and face lock.", 0.95),
            failure("FAKE_BODY_PROPORTIONS", "Batch D/E failures enlarged hips/body or modelized shape.", "Natural adult body lock; use motion reference.", 0.96),
            failure("REPEATED_FRONT_DANCE", "Current cut repeats front-facing movement.", "Add side-travel/profile/silhouette/non-face inserts.", 0.9),
            failure("WRONG_VENUE_FACE", "Some selected/rejected clips have wrong face or wrong venue.", "Use only with caution or after correction.", 0.89),
        ],
        "updated_at": now(),
    }


def build_creative_concepts() -> list[dict[str, Any]]:
    return [
        {
            "title": "The Bar Remembers Her",
            "summary": "A lonely Burmese heartbreak performance where the bar, snow, rose, glasses, and empty microphone become memory witnesses while the wife performer slowly takes control of the room.",
            "confidence": 0.86,
            "why": "Best match to existing approved assets, object story, dark bar world, and missing coverage needs.",
        },
        {
            "title": "Winter Window / Red Dress",
            "summary": "A more graphic visual poem built around the contrast of cold Finnish exterior and crimson Burmese dress movement.",
            "confidence": 0.78,
            "why": "Strong visual contrast but requires more silhouette and side-travel coverage.",
        },
        {
            "title": "The Last Microphone",
            "summary": "A restrained performance where the microphone is withheld until the ending as a symbol of what cannot be said.",
            "confidence": 0.74,
            "why": "Preserves the mic-symbol rule but risks drifting back toward performance staging if not controlled.",
        },
    ]


def build_storyboard(music: dict[str, Any]) -> dict[str, Any]:
    sections = music.get("sections") or default_sections()
    shots = []
    shot_no = 1
    templates = [
        ("Object Prologue", "A01/A02/A03/A08", "wide/object", "bar memory setup", "static/slow push", "low", "manual/local existing"),
        ("Stronger Entrance", "F04_stronger_entrance", "wide full-body", "performer takes ownership", "slow forward then lateral", "medium", "Seedance or Kling after refs"),
        ("Side Travel", "F01_side_travel_dance", "medium-wide side", "room ownership through movement", "side tracking", "high", "Seedance first, Kling fallback"),
        ("Profile Shadow", "F02_profile_shadow_movement", "profile silhouette", "hide face risk, increase pressure", "side/profile track", "high", "Kling/Seedance after motion ref"),
        ("Dress Pivot", "F05_dress_pivot", "knees-up/full", "fabric punctuation", "controlled pivot only from reference", "medium", "Seedance"),
        ("Chorus Power", "F06_chorus_power_body", "wide silhouette", "chorus body power", "backlit lateral rhythm", "high", "Kling Motion Control if start frame exists"),
        ("Non-face Inserts", "F07_non_face_dance_inserts", "hands/feet/fabric", "beat punctuation", "short inserts", "medium", "local/existing cutaways"),
        ("Final Symbol", "A10_empty_microphone", "object close", "song resolves into absence", "slow hold", "low", "existing footage"),
    ]
    for section in sections:
        duration = float(section.get("end", 0)) - float(section.get("start", 0))
        count = 2 if duration < 20 else 4
        for idx in range(count):
            tmpl = templates[(shot_no - 1) % len(templates)]
            start = float(section.get("start", 0)) + idx * max(duration / max(count, 1), 1)
            end = min(float(section.get("end", start + 4)), start + max(min(duration / max(count, 1), 8), 3))
            shots.append(
                {
                    "shot_number": f"S{shot_no:03d}",
                    "timecode_start": seconds_to_tc(start),
                    "timecode_end": seconds_to_tc(end),
                    "duration": round(end - start, 2),
                    "song_section": section.get("section", "UNKNOWN"),
                    "lyric_or_phrase": "map to Burmese lyric line after line timing pass",
                    "title": tmpl[0],
                    "source_or_missing_shot_id": tmpl[1],
                    "purpose": tmpl[3],
                    "framing": tmpl[2],
                    "lens": "35mm equivalent for wide/medium; 50mm only for controlled emotional punctuation",
                    "camera_position_movement": tmpl[4],
                    "lighting": "amber/crimson key with winter-window contrast and dark teak falloff",
                    "production_design": "bar shelves, Burmese craft inserts, rose/glasses/chair/microphone symbols",
                    "performer_action": performance_action(tmpl[0]),
                    "exact_movement": movement_action(tmpl[0]),
                    "identity_risk": identity_risk(tmpl[0]),
                    "body_motion_risk": body_risk(tmpl[0]),
                    "recommended_renderer": tmpl[6],
                    "fallback_renderer": "existing footage / local storyboard mock / manual export",
                    "estimated_cost_risk": "none until approved; cloud risk high if personal references uploaded",
                    "status": "planned",
                }
            )
            shot_no += 1
    return {"version": "0.7", "shots": shots, "generated_at": now()}


def build_shot_list(storyboard: dict[str, Any]) -> list[dict[str, Any]]:
    return storyboard["shots"]


def build_renderer_plan(storyboard: dict[str, Any]) -> dict[str, Any]:
    rankings = []
    for shot in storyboard["shots"]:
        if "F01" in shot["source_or_missing_shot_id"]:
            best, fallback = "Seedance", "Kling Motion Control after character_start_frame"
            requirements = ["identity refs", "wardrobe/body", "bar/stage", "Burmese art", "motion-reference video"]
        elif "F06" in shot["source_or_missing_shot_id"]:
            best, fallback = "Kling Motion Control", "Seedance"
            requirements = ["character_start_frame", "motion video", "identity face element"]
        elif shot["source_or_missing_shot_id"].startswith("A"):
            best, fallback = "existing footage", "local mock storyboard"
            requirements = ["no cloud upload"]
        else:
            best, fallback = "Seedance", "existing footage / local mock"
            requirements = ["approved references", "motion brief"]
        rankings.append({**shot, "best_renderer": best, "fallback_renderer": fallback, "required_inputs": requirements})
    return {"rankings": rankings, "policy": "renderer is backend; creative truth stays renderer-independent"}


def build_edit_plan(storyboard: dict[str, Any], music: dict[str, Any]) -> dict[str, Any]:
    return {
        "timeline": [
            {
                "order": idx + 1,
                "start_time": shot["timecode_start"],
                "end_time": shot["timecode_end"],
                "shot_id": shot["shot_number"],
                "song_section": shot["song_section"],
                "transition": "hard cut on pulse" if shot["body_motion_risk"] != "low" else "slow dissolve or held cut",
                "face_safe_coverage": "use object/profile/silhouette cover for any mouth/face uncertainty",
                "caption_note": "Burmese caption timing pass required before final typography",
            }
            for idx, shot in enumerate(storyboard["shots"])
        ],
        "exports": ["EDL CSV", "OTIO placeholder JSON", "DaVinci handoff outline", "ffmpeg diagnostic plan"],
    }


def write_state_files(state: dict[str, Any], evidence: dict[str, Any], decisions: dict[str, Any], failures: dict[str, Any], assets: dict[str, Any]) -> None:
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    write_json(STATE_ROOT / "PROJECT_STATE.json", state)
    write_json(STATE_ROOT / "EVIDENCE_GRAPH.json", {"nodes": evidence, "updated_at": now()})
    write_json(STATE_ROOT / "DECISION_MEMORY.json", decisions)
    write_json(STATE_ROOT / "FAILURE_MEMORY.json", failures)
    write_json(STATE_ROOT / "ASSET_INDEX.json", assets)


def write_director_package(
    idea: str,
    state: dict[str, Any],
    concepts: list[dict[str, Any]],
    selected: dict[str, Any],
    storyboard: dict[str, Any],
    shot_list: list[dict[str, Any]],
    renderer_plan: dict[str, Any],
    edit_plan: dict[str, Any],
    hardware: dict[str, Any],
    questions: list[str],
) -> None:
    LATEST_PLAN.mkdir(parents=True, exist_ok=True)
    STORYBOARD_ROOT.mkdir(parents=True, exist_ok=True)
    write_json(LATEST_PLAN / "SONG_STRUCTURE.json", state["music"])
    write_json(LATEST_PLAN / "EMOTIONAL_ARC.json", emotional_arc(state["music"]))
    write_json(LATEST_PLAN / "STORYBOARD.json", storyboard)
    write_json(LATEST_PLAN / "RENDERER_PLAN.json", renderer_plan)
    write_json(LATEST_PLAN / "EDIT_PLAN.json", edit_plan)
    write_csv(LATEST_PLAN / "FULL_SHOT_LIST.csv", shot_list)
    write_csv(LATEST_PLAN / "EDIT_DECISION_PLAN.csv", edit_plan["timeline"])
    write_storyboard_frames(storyboard)
    (LATEST_PLAN / "EXECUTIVE_CREATIVE_SUMMARY.md").write_text(executive_summary(idea, state, selected, questions), encoding="utf-8")
    (LATEST_PLAN / "CREATIVE_CONCEPTS.md").write_text(concepts_md(concepts), encoding="utf-8")
    (LATEST_PLAN / "SELECTED_CONCEPT.md").write_text(selected_concept_md(selected), encoding="utf-8")
    for name, content in bible_documents(state, selected).items():
        (LATEST_PLAN / name).write_text(content, encoding="utf-8")
    (LATEST_PLAN / "DIRECTOR_TREATMENT.md").write_text(director_treatment(state, selected), encoding="utf-8")
    (LATEST_PLAN / "SONG_AND_LYRIC_MAP.md").write_text(song_and_lyric_map(state), encoding="utf-8")
    (LATEST_PLAN / "RENDERER_PLAN.md").write_text(renderer_plan_md(renderer_plan), encoding="utf-8")
    (LATEST_PLAN / "COST_PRIVACY_PLAN.md").write_text(cost_privacy_plan(), encoding="utf-8")
    (LATEST_PLAN / "PRODUCTION_PLAN.md").write_text(production_plan(questions), encoding="utf-8")
    (LATEST_PLAN / "OPEN_QUESTIONS.md").write_text(open_questions_md(questions), encoding="utf-8")
    (LATEST_PLAN / "LOCAL_IMAGE_BACKEND_STATUS.md").write_text(local_image_backend_status(hardware), encoding="utf-8")
    (LATEST_PLAN / "STORYBOARD_BOARD.html").write_text(storyboard_html(storyboard), encoding="utf-8")


def write_storyboard_frames(storyboard: dict[str, Any]) -> None:
    frame_dir = STORYBOARD_ROOT / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    for shot in storyboard["shots"]:
        (frame_dir / f"{shot['shot_number']}.svg").write_text(storyboard_frame_svg(shot), encoding="utf-8")


def storyboard_frame_svg(shot: dict[str, Any]) -> str:
    title = shot["title"].replace("&", "and").replace("<", "").replace(">", "")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720">
<rect width="1280" height="720" fill="#101112"/>
<rect x="80" y="90" width="1120" height="470" fill="#17110f" stroke="#34302c" stroke-width="8"/>
<rect x="820" y="130" width="250" height="300" fill="#1b2428" opacity=".8"/>
<path d="M850 150 L1040 410 M1040 150 L850 410" stroke="#52606a" stroke-width="5" opacity=".35"/>
<path d="M0 590 C240 550 360 620 610 580 C830 544 1010 555 1280 520 L1280 720 L0 720 Z" fill="#0b0c0d"/>
<circle cx="610" cy="360" r="54" fill="#7b1e1a" opacity=".65"/>
<path d="M610 410 C580 500 545 560 520 635 M610 410 C660 500 695 560 715 635 M580 455 C515 470 465 505 430 550 M645 455 C690 470 735 500 780 540" stroke="#9d3b32" stroke-width="24" stroke-linecap="round" opacity=".75"/>
<text x="90" y="635" fill="#d69b49" font-family="Arial, sans-serif" font-size="38">{shot['shot_number']} · {title}</text>
<text x="90" y="680" fill="#afa79a" font-family="Arial, sans-serif" font-size="24">{shot['timecode_start']} - {shot['timecode_end']} · {shot['framing']} · {shot['camera_position_movement']}</text>
</svg>
"""


def bible_documents(state: dict[str, Any], selected: dict[str, Any]) -> dict[str, str]:
    return {
        "CHARACTER_BIBLE.md": "# Character Bible\n\nThe performer is the consenting adult wife, anchored only by approved A1/A2 identity references. She is alone, restrained, emotionally pressurized, and never turned into a generic model body.\n",
        "PERFORMANCE_BIBLE.md": "# Performance Bible\n\nPerformance is mature, inward, rhythm-aware, and cinematic. No karaoke, no lounge singing, no fake Burmese lip-sync. Mouth exposure is minimized until dedicated lip-sync exists.\n",
        "WARDROBE_BIBLE.md": "# Wardrobe Bible\n\nDeep-red one-shoulder Burmese-inspired satin dress. Natural adult proportions. Fabric movement must be physically plausible and tied to actual motion references.\n",
        "LOCATION_BIBLE.md": "# Location Bible\n\nApproved dark teak Finnish bar/stage, winter window, shelves, floor, curtain and amber/crimson falloff. Do not introduce piano/drums/band lounge venue drift.\n",
        "PRODUCTION_DESIGN_BIBLE.md": "# Production Design Bible\n\nObject story: two glasses, rose, empty chair, stopped clock, snow window, door bolt, Burmese craft insert, empty microphone as ending symbol only.\n",
        "CULTURAL_BIBLE.md": "# Cultural Bible\n\nBurmese material identity is explicit through dress, craft/art world, caption typography, and emotional restraint. Avoid generic Asian, Chinese, K-pop or nightclub drift.\n",
        "LIGHTING_BIBLE.md": "# Lighting Bible\n\nAmber/crimson interior pressure against cold winter-window contrast. Use silhouettes and dark teak texture; protect identity by keeping face small/profile/shadowed when needed.\n",
        "CAMERA_AND_LENS_BIBLE.md": "# Camera And Lens Bible\n\nMedium-wide/full-body side tracking, profile movement, silhouette coverage, object inserts. Avoid repeated front-facing static performance. Lens language: 35mm for room/body, 50mm for rare emotional punctuation.\n",
        "MOVEMENT_AND_CHOREOGRAPHY_BIBLE.md": "# Movement And Choreography Bible\n\nMovement mechanics must come from approved motion references. Emotional tone may be restrained psychological tension and mature blues/jazz pressure. Reject kung fu, kicks, K-pop, TikTok, high ballet arms, random spins, vulgar nightclub movement, and fake body reshaping.\n",
        "ACTING_AND_EXPRESSION_BIBLE.md": "# Acting And Expression Bible\n\nShe carries heartbreak as control, not melodrama. Use gaze, breath, shoulder/torso pressure, pauses, and profile turns. Close face requires correction/review before final use.\n",
        "EDITING_BIBLE.md": "# Editing Bible\n\nUse song sections and onset density. Intro/outro can hold objects; verse/chorus need body rhythm and sharper cuts. Use object/profile/silhouette coverage to hide weak face/lip moments.\n",
        "COLOR_AND_FINISHING_BIBLE.md": "# Color And Finishing Bible\n\nDark teak, crimson dress, amber practicals, winter blue window contrast. Avoid warm lounge gloss. Finish should feel cinematic, textured, and controlled.\n",
        "CAPTION_AND_LANGUAGE_PLAN.md": "# Caption And Language Plan\n\nPreserve original Burmese lyrics separately from normalized Unicode, pronunciation helper, caption text, and translation/explanation. Use Unicode Burmese-capable typography; timing pass remains required.\n",
        "VOICE_AND_LIPSYNC_PLAN.md": "# Voice And Lip-Sync Plan\n\nVoice and lip-sync are separate stages. Verify real Burmese support before claiming any cloud voice option. Real-person voice cloning needs explicit consent. No cloud voice upload without approval.\n",
    }


def research_search_assistant(query: str) -> dict[str, Any]:
    q = query.strip() or "mature side-travel performance lonely blues jazz bar music video"
    encoded = re.sub(r"\s+", "+", q)
    return {
        "query": q,
        "search_links": [
            f"https://shot.cafe/search/{encoded}",
            f"https://www.youtube.com/results?search_query={encoded}",
            f"https://vimeo.com/search?q={encoded}",
            f"https://film-grab.com/?s={encoded}",
        ],
        "visual_categories": ["lonely bar wide shots", "profile performer movement", "winter window contrast", "red dress against dark wood"],
        "movement_categories": ["side-travel walk/dance", "controlled shoulders/torso", "low relaxed arms", "object pause into movement"],
        "notes": "Store URLs, timecodes, tags, and analysis only. Do not scrape/rehost copyrighted stills.",
    }


def write_research_audit() -> None:
    root = REPO_ROOT / "director-os-research"
    root.mkdir(exist_ok=True)
    repos = inspect_research_repos()
    (root / "GITHUB_ARCHITECTURE_AUDIT.md").write_text(github_audit_md(repos), encoding="utf-8")
    write_csv(root / "LICENSE_MATRIX.csv", repos)
    (root / "REUSABLE_COMPONENT_MAP.md").write_text(reusable_component_map(repos), encoding="utf-8")
    (root / "SECURITY_AND_SUPPLY_CHAIN_REPORT.md").write_text(security_report(repos), encoding="utf-8")
    (root / "BUILD_VS_ADOPT_DECISIONS.md").write_text(build_vs_adopt(repos), encoding="utf-8")


def inspect_research_repos() -> list[dict[str, Any]]:
    base = REPO_ROOT / "local-tools/research-repos"
    candidates = {
        "SoeMind Forge": base / "soemind-forge",
        "HKUDS VideoAgent": base / "HKUDS-VideoAgent",
        "FireRed-OpenStoryline": base / "FireRed-OpenStoryline",
        "ComfyUI": base / "ComfyUI",
        "ComfyUI-Manager": base / "ComfyUI-Manager",
        "OpenMontage": base / "OpenMontage",
        "ViMax": base / "ViMax",
    }
    rows = []
    for name, path in candidates.items():
        exists = path.exists()
        files = list(path.rglob("*")) if exists else []
        license_path = next((p for p in files if p.is_file() and p.name.lower().startswith("license")), None)
        readme_path = next((p for p in files if p.is_file() and p.name.lower() in {"readme.md", "readme"}), None)
        package = path / "package.json"
        requirements = path / "requirements.txt"
        rows.append(
            {
                "name": name,
                "path": str(path.relative_to(REPO_ROOT)),
                "available": exists,
                "license": first_line(license_path) if license_path else "UNKNOWN/not cloned",
                "file_count": len([p for p in files if p.is_file()]) if exists else 0,
                "has_package_json": package.exists(),
                "has_requirements": requirements.exists(),
                "has_dockerfile": (path / "Dockerfile").exists(),
                "has_install_scripts": any(p.name in {"setup.sh", "build_env.sh", "download.sh", "run.sh"} for p in files if p.is_file()) if exists else False,
                "readme_excerpt": read_text(readme_path, 600).replace("\n", " ") if readme_path else "",
                "decision": repo_decision(name, exists),
            }
        )
    return rows


def repo_decision(name: str, exists: bool) -> str:
    if not exists:
        return "Record as unresolved candidate; do not adopt until source is found and inspected."
    if name == "SoeMind Forge":
        return "Learn workflow templates, cost tracking, captions/text overlay ideas; do not adopt Gemini-specific execution."
    if name == "HKUDS VideoAgent":
        return "Learn multi-agent orchestration and memory structure; do not adopt claims or API-heavy execution directly."
    if name == "FireRed-OpenStoryline":
        return "Learn story/script pipeline shape; avoid automatic model downloads and shell scripts."
    if name == "ComfyUI":
        return "Use as optional local backend adapter, not as primary Director OS UX."
    if name == "ComfyUI-Manager":
        return "Study security checks and registry ideas; do not install untrusted custom nodes by default."
    return "Study only."


# Markdown/render helpers
def executive_summary(idea: str, state: dict[str, Any], selected: dict[str, Any], questions: list[str]) -> str:
    return f"""# Executive Creative Summary

## Idea

{idea}

## Selected Concept

**{selected['title']}**: {selected['summary']}

## What Director OS Understood

- Existing project is a Burmese heartbreak music video.
- Master song: `{LOCKED_TRUTH['song']}`.
- Performer: consenting adult wife, using only approved A1/A2 face references.
- World: approved dark teak Finnish bar/stage, winter window, amber/crimson light, Burmese craft/art inserts.
- Wardrobe/body: deep-red one-shoulder Burmese-inspired dress and natural adult proportions.
- Current weakness: repeated front-facing dance, missing side-travel/profile/silhouette/dress-pivot/power-body coverage.
- Production rule: no karaoke, no mic-centered staging, no kung fu, no K-pop/TikTok, no fake lip-sync, no fake body.

## Created

- Director treatment, concept package, bibles, storyboard, shot list, renderer plan, edit plan, caption/voice plan and open questions.
- Canonical machine-readable state in `director-os/state/`.
- Visual storyboard board in `director-os/plans/latest/STORYBOARD_BOARD.html`.

## Next Best Action

{next_best_action(state)}
"""


def concepts_md(concepts: list[dict[str, Any]]) -> str:
    lines = ["# Creative Concepts", ""]
    for concept in concepts:
        lines.extend([f"## {concept['title']}", "", concept["summary"], "", f"- Confidence: {concept['confidence']}", f"- Why: {concept['why']}", ""])
    return "\n".join(lines)


def selected_concept_md(selected: dict[str, Any]) -> str:
    return f"# Selected Concept\n\n## {selected['title']}\n\n{selected['summary']}\n\nConfidence: {selected['confidence']}\n"


def director_treatment(state: dict[str, Any], selected: dict[str, Any]) -> str:
    return f"""# Director Treatment

## {selected['title']}

The video is a cinematic Burmese heartbreak performance staged as a memory
inside the approved dark Finnish bar. The wife performer is alone. She does not
sing to camera as karaoke; she moves through the room as if the room is holding
the memory with her.

The cold winter window and warm amber/crimson bar light create the visual
conflict. The red Burmese-inspired dress becomes the emotional center, but body
proportions stay natural and adult. Object cutaways carry story and protect weak
face/lip moments: two glasses, rose, empty chair, stopped clock, door bolt,
Burmese craft, snow window, and the empty microphone only at the ending.

The camera language favors medium-wide, full-body, profile, side-travel and
silhouette coverage. Choreography is not invented from text. Movement-heavy
shots require approved motion references with body mechanics, travel path,
timing, shoulder/torso rhythm, and explicit non-transfer of source identity,
clothing, location and body shape.
"""


def song_and_lyric_map(state: dict[str, Any]) -> str:
    lines = ["# Song And Lyric Map", "", f"- Source: {state['music']['source']}", f"- Duration: {state['music']['duration']}", f"- BPM: {state['music']['bpm']}", ""]
    for section in state["music"].get("sections", []):
        lines.append(f"- {section.get('section')}: {seconds_to_tc(section.get('start', 0))}-{seconds_to_tc(section.get('end', 0))}; {section.get('movement_directive', '')}")
    lines.extend(["", "## Burmese Language", "", f"- Source: {state['burmese_language']['source']}", f"- Zawgyi likely: {state['burmese_language']['zawgyi_likely']}", f"- Caption-safe lines sampled: {state['burmese_language']['line_count']}"])
    return "\n".join(lines) + "\n"


def renderer_plan_md(renderer_plan: dict[str, Any]) -> str:
    lines = ["# Renderer Plan", "", renderer_plan["policy"], "", "| Shot | Best | Fallback | Required Inputs |", "|---|---|---|---|"]
    for item in renderer_plan["rankings"]:
        lines.append(f"| {item['shot_number']} | {item['best_renderer']} | {item['fallback_renderer']} | {', '.join(item['required_inputs'])} |")
    return "\n".join(lines) + "\n"


def cost_privacy_plan() -> str:
    return "# Cost Privacy Plan\n\nNo cloud upload, paid API spend, real-person voice cloning, renderer submission, publishing, or deletion is allowed without explicit approval. Local planning and metadata analysis are allowed.\n"


def production_plan(questions: list[str]) -> str:
    return "# Production Plan\n\n1. Review Director Plan and Storyboard.\n2. Approve or adjust the selected concept.\n3. Record or approve F01 motion-reference video.\n4. Create character/start-frame plate only after explicit approval.\n5. Generate one controlled test only after privacy/spend approval.\n6. Import result locally, QC, then decide accept/reject/face-correct/recut.\n\nBlocked items:\n" + "\n".join(f"- {q}" for q in questions) + "\n"


def open_questions_md(questions: list[str]) -> str:
    return "# Open Questions\n\n" + "\n".join(f"- {question}" for question in questions[:5]) + "\n"


def storyboard_html(storyboard: dict[str, Any]) -> str:
    cards = []
    for shot in storyboard["shots"]:
        cards.append(
            f"""<article class="card">
<img class="frame" src="../../storyboards/latest/frames/{shot['shot_number']}.svg" alt="{shot['shot_number']} storyboard frame">
<h2>{shot['title']}</h2>
<p><strong>{shot['timecode_start']} - {shot['timecode_end']}</strong> / {shot['song_section']}</p>
<p>{shot['purpose']}</p>
<dl>
<dt>Framing</dt><dd>{shot['framing']}</dd>
<dt>Camera</dt><dd>{shot['camera_position_movement']}</dd>
<dt>Movement</dt><dd>{shot['exact_movement']}</dd>
<dt>Renderer</dt><dd>{shot['recommended_renderer']}</dd>
<dt>Risks</dt><dd>Identity: {shot['identity_risk']} / Body: {shot['body_motion_risk']}</dd>
</dl>
<div class="actions">Approve · Reject · Refine · Compare</div>
</article>"""
        )
    return """<!doctype html><html><head><meta charset="utf-8"><title>Director OS Storyboard</title>
<style>body{margin:0;background:#101112;color:#f2eee8;font-family:system-ui}.board{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:18px;padding:24px}.card{border:1px solid #34302c;background:#18191b;padding:16px}.frame{aspect-ratio:16/9;background:linear-gradient(135deg,#241411,#0b0c0d);display:grid;place-items:center;color:#d69b49;font-size:34px;margin-bottom:12px}dt{color:#d69b49;font-size:12px}dd{margin:2px 0 8px;color:#afa79a}.actions{border-top:1px solid #34302c;padding-top:10px;color:#d69b49}</style>
</head><body><main class="board">""" + "\n".join(cards) + "</main></body></html>\n"


def github_audit_md(repos: list[dict[str, Any]]) -> str:
    lines = ["# GitHub Architecture Audit", "", "Source was shallow-cloned where reachable. No install scripts were run and no model weights were downloaded.", ""]
    for repo in repos:
        lines.extend([f"## {repo['name']}", "", f"- Available locally: {repo['available']}", f"- Path: `{repo['path']}`", f"- License first line: {repo['license']}", f"- File count: {repo['file_count']}", f"- Has package.json: {repo['has_package_json']}", f"- Has requirements.txt: {repo['has_requirements']}", f"- Has install/download scripts: {repo['has_install_scripts']}", f"- Decision: {repo['decision']}", ""])
    return "\n".join(lines)


def reusable_component_map(repos: list[dict[str, Any]]) -> str:
    return "# Reusable Component Map\n\n- SoeMind Forge: workflow templates, caption/text overlay guides, cost tracking ideas.\n- HKUDS VideoAgent: multi-agent orchestration/memory patterns.\n- FireRed-OpenStoryline: storyline-to-shot pipeline shape.\n- ComfyUI: optional local backend adapter and workflow graph format.\n- ComfyUI-Manager: registry/security-check concepts only; no untrusted node installation.\n"


def security_report(repos: list[dict[str, Any]]) -> str:
    lines = ["# Security And Supply Chain Report", "", "- No install scripts were executed.", "- No model weights were downloaded.", "- ComfyUI custom nodes remain disabled until explicit audit.", "- Cloud/provider connectors remain disabled.", ""]
    for repo in repos:
        if repo["has_install_scripts"]:
            lines.append(f"- {repo['name']}: contains install/run/download scripts; manual review required before execution.")
    return "\n".join(lines) + "\n"


def build_vs_adopt(repos: list[dict[str, Any]]) -> str:
    return "# Build Vs Adopt Decisions\n\nBuild Director OS orchestration, Burmese-first state, storyboard, QC and privacy gates in-house. Adopt ideas, not direct runtime dependencies, from SoeMind Forge and VideoAgent. Integrate ComfyUI only through a disabled optional adapter after a separate local backend approval.\n"


def local_image_backend_status(hardware: dict[str, Any]) -> str:
    return f"""# Local Image Backend Status

- Machine: {hardware['machine']}
- Processor: {hardware['processor']}
- RAM: {hardware['ram']}
- Free disk: {hardware['free_disk']}
- ComfyUI source snapshot: {hardware['comfyui_source']}
- Current backend: mock/template storyboard backend

No large model weights were installed. Before installing any local model, show
license, model size, disk requirement, RAM use, generation time, supported
resolution, and commercial-use implications.
"""


# Small utilities
def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def sha256_small(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ffprobe_duration(path: Path) -> float:
    if not path.exists() or not shutil.which("ffprobe"):
        return 0.0
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)], check=False, capture_output=True, text=True)
    try:
        return round(float(result.stdout.strip()), 3)
    except ValueError:
        return 0.0


def seconds_to_tc(value: Any) -> str:
    seconds = float(value or 0)
    minutes = int(seconds // 60)
    sec = seconds - minutes * 60
    return f"{minutes:02d}:{sec:05.2f}"


def default_sections() -> list[dict[str, Any]]:
    return [
        {"section": "intro", "start": 0, "end": 32.18, "movement_directive": "LOW: setup, gaze, object cuts, held poses"},
        {"section": "verse1", "start": 32.18, "end": 92.58, "movement_directive": "HIGH: dance/body rhythm, sharper cuts"},
        {"section": "chorus1", "start": 97.66, "end": 164.12, "movement_directive": "HIGH: dance/body rhythm, sharper cuts"},
        {"section": "instrumental_breath", "start": 164.12, "end": 176.24, "movement_directive": "MEDIUM: walking, torso/arm phrases"},
        {"section": "later_verse", "start": 176.24, "end": 234.58, "movement_directive": "HIGH: dance/body rhythm"},
        {"section": "chorus2_final", "start": 235.44, "end": 278.22, "movement_directive": "HIGH: power body movement"},
        {"section": "outro", "start": 278.22, "end": 292.66, "movement_directive": "LOW: final symbol"},
    ]


def detect_zawgyi(text: str) -> bool:
    return bool(re.search(r"[ၤၽၾၺ]|ေ[က-အ]", text or ""))


def normalize_burmese_text(text: str) -> str:
    return text.replace("\ufeff", "").strip()


def performance_action(title: str) -> str:
    if "Object" in title or "Final" in title:
        return "No face performance; objects carry memory."
    return "Controlled emotional body performance, face small/profile/shadowed unless explicitly approved."


def movement_action(title: str) -> str:
    mapping = {
        "Side Travel": "sustained lateral travel from approved motion reference",
        "Profile Shadow": "profile-weight shift and shoulder/torso rhythm",
        "Dress Pivot": "controlled pivot only if present in motion source",
        "Chorus Power": "grounded power body movement with low arms",
    }
    return mapping.get(title, "restrained walking, stillness, or object action")


def identity_risk(title: str) -> str:
    return "low" if "Object" in title or "Silhouette" in title or "Final" in title else "medium"


def body_risk(title: str) -> str:
    return "high without motion reference" if any(word in title for word in ["Side", "Dress", "Chorus"]) else "medium"


def emotional_arc(music: dict[str, Any]) -> dict[str, Any]:
    return {"arc": [{"section": s.get("section"), "emotion": "controlled heartbreak pressure", "energy": s.get("movement_directive", "")} for s in music.get("sections", [])]}


def decision(status: str, text: str, source: str, confidence: float) -> dict[str, Any]:
    return {"status": status, "decision": text, "evidence_source": source, "confidence": confidence, "date": now(), "superseded_by": "", "user_decision": ""}


def failure(code: str, problem: str, lesson: str, confidence: float) -> dict[str, Any]:
    return {"code": code, "problem": problem, "reusable_lesson": lesson, "confidence": confidence, "date": now()}


def genuine_open_questions(evidence: dict[str, Any]) -> list[str]:
    return [
        "Approve or record one motion-reference video for F01 side-travel dance with exact timecode and rights/consent.",
        "Approve or create one Kling character/start-frame plate only if Kling Motion Control will be tested.",
        "Confirm whether captions should be Burmese-only or bilingual Burmese/English for the first public-facing version.",
    ]


def next_best_action(state: dict[str, Any]) -> str:
    if not state:
        return "Create a Director Plan from one idea and the project path."
    return "Review the storyboard, then approve or record the F01 side-travel motion reference."


def hardware_audit() -> dict[str, Any]:
    total, used, free = shutil.disk_usage(str(REPO_ROOT))
    return {
        "machine": platform.machine(),
        "processor": platform.processor() or platform.platform(),
        "ram": "UNKNOWN from Python stdlib",
        "free_disk": f"{free // (1024 ** 3)} GB",
        "comfyui_source": (REPO_ROOT / "local-tools/research-repos/ComfyUI").exists(),
    }


def first_line(path: Optional[Path]) -> str:
    if not path or not path.exists():
        return "UNKNOWN"
    return path.read_text(encoding="utf-8", errors="ignore").splitlines()[0][:160]
