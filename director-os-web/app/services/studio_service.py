from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.audio_truth.orchestrator import run_audio_truth_engine
from app.config import ENGINE_ROOT, REPO_ROOT
from app.audio.brain_sync_service import brain_timeline_status, rebuild_caption_v6
from app.services.director_workspace_service import list_storyboard_cards, sync_workspace_from_latest_plan
from app.services.latest_safe_animatic_service import latest_safe_animatic_context
from app.studio_loop.orchestrator import DEFAULT_STUDIO_IDEA, create_studio_loop, latest_loop, run_studio_loop
from app.system_tools.ffmpeg_service import probe_media, run_ffmpeg


PROJECTS_ROOT = ENGINE_ROOT / "projects"
DEFAULT_PROJECT_ID = "burmese-music-video"
ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".heic",
    ".webp",
    ".mp4",
    ".mov",
    ".webm",
    ".mp3",
    ".wav",
    ".m4a",
    ".flac",
    ".txt",
    ".srt",
    ".vtt",
    ".ass",
    ".pdf",
}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac"}
TEXT_EXTENSIONS = {".txt", ".srt", ".vtt", ".ass"}


@dataclass(frozen=True)
class StudioPaths:
    root: Path
    inputs: Path
    thumbnails: Path
    contact_sheets: Path
    waveforms: Path
    previews: Path
    packages: Path


def studio_paths(project_id: str) -> StudioPaths:
    root = PROJECTS_ROOT / safe_project_id(project_id)
    return StudioPaths(
        root=root,
        inputs=root / "inputs",
        thumbnails=root / "thumbnails",
        contact_sheets=root / "contact-sheets",
        waveforms=root / "waveforms",
        previews=root / "previews",
        packages=root / "production-packages",
    )


def studio_home_context() -> dict[str, Any]:
    ensure_default_project()
    projects = list_projects()
    selected = project_context(DEFAULT_PROJECT_ID)
    return {
        "projects": projects,
        "selected": selected,
        "default_idea": DEFAULT_STUDIO_IDEA,
        "latest_loop": latest_loop(),
        "safe_animatic": latest_safe_animatic_context(),
    }


def create_project(name: str = "Untitled Studio Project") -> dict[str, Any]:
    project_id = safe_project_id(name) or "studio-project"
    original = project_id
    counter = 2
    while (PROJECTS_ROOT / project_id / "PROJECT.json").exists():
        project_id = f"{original}-{counter}"
        counter += 1
    paths = studio_paths(project_id)
    _ensure_project_dirs(paths)
    state = {
        "project_id": project_id,
        "name": name,
        "source_project_path": str(REPO_ROOT),
        "status": "created",
        "rights": "local_user_supplied_or_existing_project",
        "privacy": "local_only_no_upload",
        "latest_loop_id": "",
        "latest_result": "",
    }
    write_json(paths.root / "PROJECT.json", state)
    write_json(paths.root / "INPUTS.json", {"inputs": []})
    return state


def ensure_default_project() -> dict[str, Any]:
    paths = studio_paths(DEFAULT_PROJECT_ID)
    if (paths.root / "PROJECT.json").exists():
        return read_json(paths.root / "PROJECT.json")
    state = create_project("Burmese Music Video")
    if state["project_id"] != DEFAULT_PROJECT_ID:
        paths = studio_paths(DEFAULT_PROJECT_ID)
        _ensure_project_dirs(paths)
        state["project_id"] = DEFAULT_PROJECT_ID
        state["name"] = "Burmese Music Video"
        write_json(paths.root / "PROJECT.json", state)
        write_json(paths.root / "INPUTS.json", {"inputs": []})
    return state


def list_projects() -> list[dict[str, Any]]:
    PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
    projects = []
    for path in sorted(PROJECTS_ROOT.iterdir()):
        project_file = path / "PROJECT.json"
        if project_file.exists():
            projects.append(read_json(project_file))
    return projects


async def ingest_uploads(project_id: str, files: list[Any]) -> dict[str, Any]:
    paths = studio_paths(project_id)
    _ensure_project_dirs(paths)
    records = read_json(paths.root / "INPUTS.json", {"inputs": []}).get("inputs", [])
    existing_hashes = {record.get("sha256") for record in records}
    added: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for upload in files:
        if not upload.filename:
            continue
        original_name = Path(upload.filename).name
        safe_name = sanitize_filename(original_name)
        suffix = Path(safe_name).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            rejected.append({"filename": original_name, "reason": "unsupported_file_type"})
            continue
        temp_path = paths.inputs / f".upload-{safe_name}"
        with temp_path.open("wb") as output:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
        sha = sha256_file(temp_path)
        if sha in existing_hashes:
            if temp_path.exists():
                temp_path.unlink()
            rejected.append({"filename": original_name, "reason": "duplicate_hash", "sha256": sha})
            continue
        stored_name = f"{sha[:12]}-{safe_name}"
        stored_path = paths.inputs / stored_name
        temp_path.replace(stored_path)
        record = build_input_record(project_id, stored_path, original_name, sha)
        records.append(record)
        added.append(record)
        existing_hashes.add(sha)
    write_json(paths.root / "INPUTS.json", {"inputs": records, "rejected_uploads": rejected})
    scan = project_scan(project_id)
    return {"project_id": project_id, "added": added, "rejected": rejected, "scan": scan}


def project_context(project_id: str) -> dict[str, Any]:
    ensure_default_project() if project_id == DEFAULT_PROJECT_ID else None
    paths = studio_paths(project_id)
    project = read_json(paths.root / "PROJECT.json", {})
    inputs = read_json(paths.root / "INPUTS.json", {"inputs": []})
    scan = project_scan(project_id)
    result = read_json(paths.root / "RESULT.json", {})
    autopilot = read_json(paths.root / "AUTOPILOT_V25_STATUS.json", {})
    inventory = read_json(paths.root / "ALREADY_AVAILABLE_INVENTORY.json", {})
    font_status = read_json(ENGINE_ROOT / "captions" / "font-validation-v2" / "FONT_READABILITY_STATUS.json", {})
    caption_status = read_json(ENGINE_ROOT / "captions" / "audio-truth-v5" / "CAPTION_ACCURACY_STATUS.json", {})
    return {
        "project": project,
        "paths": {k: str(v) for k, v in paths.__dict__.items()},
        "inputs": inputs.get("inputs", []),
        "rejected_uploads": inputs.get("rejected_uploads", []),
        "scan": scan,
        "result": result,
        "autopilot": autopilot,
        "inventory": inventory,
        "font_status": font_status,
        "caption_status": caption_status,
        "latest_loop": latest_loop(),
        "safe_animatic": latest_safe_animatic_context(),
    }


def project_scan(project_id: str) -> dict[str, Any]:
    paths = studio_paths(project_id)
    inputs = read_json(paths.root / "INPUTS.json", {"inputs": []}).get("inputs", [])
    state = read_json(ENGINE_ROOT / "state" / "PROJECT_STATE.json", {})
    asset_index = read_json(ENGINE_ROOT / "state" / "ASSET_INDEX.json", {})
    counts = {
        "performer_identity": 0,
        "body_full_body": 0,
        "wardrobe": 0,
        "location": 0,
        "environment": 0,
        "cultural_artwork": 0,
        "props": 0,
        "object_insert": 0,
        "motion_reference": 0,
        "voice_reference": 0,
        "music": 0,
        "lyrics": 0,
        "footage": 0,
        "generated_result": 0,
        "rejected": 0,
        "restricted": 0,
        "unknown": 0,
    }
    for record in inputs:
        role = record.get("classification", "unknown")
        counts[role] = counts.get(role, 0) + 1
    locked_truth = {
        "performer": "consenting adult wife performer",
        "face_references": ["REF-A1", "REF-A2"],
        "wardrobe": "deep-red one-shoulder Burmese-inspired dress",
        "location": "approved dark teak Finnish bar with winter window",
        "lighting": "amber/crimson cinematic lighting with cold window contrast",
        "avoid": ["karaoke", "kung fu", "K-pop", "TikTok", "fake body reshaping", "raw child-containing sources"],
    }
    approved_assets = asset_index.get("assets", []) if isinstance(asset_index, dict) else []
    summary = {
        "project_id": project_id,
        "input_count": len(inputs),
        "classifications": counts,
        "director_os_found": {
            "performer_references": "approved A1/A2 face references preserved",
            "wardrobe_references": "approved body/wardrobe reference B preserved",
            "location_references": "approved bar/stage reference C preserved",
            "song": "audio/01.mp3 master preserved",
            "lyrics": "Burmese lyric state and v6 captions preserved",
            "usable_footage": "existing project evidence scanned from prior runs",
            "motion_references": "available records preserved; new uploads auto-classified",
            "rejected_restricted_media": "rejected identity and child-containing material remain blocked",
            "missing_creative_inputs": _missing_inputs(counts),
        },
        "locked_truth": locked_truth,
        "approved_asset_count": len(approved_assets),
        "source_state_status": state.get("status", "available" if state else "missing"),
    }
    write_json(paths.root / "SCAN_SUMMARY.json", summary)
    return summary


def create_everything(project_id: str, idea: str) -> dict[str, Any]:
    paths = studio_paths(project_id)
    _ensure_project_dirs(paths)
    project_scan(project_id)
    concepts = create_concepts(project_id, idea)
    sync_workspace_from_latest_plan()
    storyboard = create_storyboard_bundle(project_id)
    sketch = create_video_sketch(project_id)
    prompts = create_prompt_packages(project_id)
    audio_truth = run_autopilot_v25()
    captions = read_json(ENGINE_ROOT / "captions" / "audio-truth-v5" / "CAPTION_ACCURACY_STATUS.json", {})
    prompts = read_json(paths.packages / "PACKAGE_MANIFEST.json", prompts)
    loop_id = create_studio_loop(idea, str(REPO_ROOT))
    loop_detail = run_studio_loop(loop_id)
    result = {
        "project_id": project_id,
        "idea": idea,
        "status": loop_detail["loop"].get("status"),
        "loop_id": loop_id,
        "concepts": concepts,
        "recommended_concept": concepts["recommended"],
        "storyboard": storyboard,
        "captions": captions,
        "video_sketch": sketch,
        "audio_truth": audio_truth,
        "prompt_packages": prompts,
        "evaluation": loop_detail.get("evaluation", {}),
        "defects": loop_detail.get("defects", {}),
        "repairs": loop_detail.get("repairs", {}),
        "next_action": loop_detail["loop"].get("next_action"),
    }
    write_json(paths.root / "RESULT.json", result)
    project = read_json(paths.root / "PROJECT.json", {})
    project.update({"status": "ready_for_review", "latest_loop_id": loop_id, "latest_result": str(paths.root / "RESULT.json")})
    write_json(paths.root / "PROJECT.json", project)
    return result


def run_autopilot_v25() -> dict[str, Any]:
    script = REPO_ROOT / "director-os-web" / "scripts" / "run_autopilot_v25.py"
    python = REPO_ROOT / ".venvs" / "audio-truth" / "bin" / "python"
    command = [str(python if python.exists() else Path("python3")), str(script)]
    result = subprocess.run(command, cwd=str(REPO_ROOT), capture_output=True, text=True, check=False)
    log = PROJECTS_ROOT / DEFAULT_PROJECT_ID / "AUTOPILOT_V25_RUN.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(result.stdout + "\n--- STDERR ---\n" + result.stderr, encoding="utf-8")
    status_path = PROJECTS_ROOT / DEFAULT_PROJECT_ID / "AUTOPILOT_V25_STATUS.json"
    status = read_json(status_path, {})
    if result.returncode != 0:
        status = {"version": "v2.5", "status": "failed", "returncode": result.returncode, "log": str(log), "error": result.stderr[-2000:]}
        write_json(status_path, status)
    return status


def continue_and_improve(project_id: str, refinement: str = "") -> dict[str, Any]:
    paths = studio_paths(project_id)
    project = read_json(paths.root / "PROJECT.json", {})
    idea = refinement.strip() or read_json(paths.root / "RESULT.json", {}).get("idea") or DEFAULT_STUDIO_IDEA
    return create_everything(project_id, idea)


def create_concepts(project_id: str, idea: str) -> dict[str, Any]:
    paths = studio_paths(project_id)
    concepts = [
        {
            "id": "concept-a",
            "title": "The Bar Remembers Her",
            "idea": "A restrained solo performance where the empty bar behaves like memory around her.",
            "palette": ["dark teak", "deep crimson", "amber practicals", "winter blue"],
            "setting": "approved Finnish bar, winter window, Burmese craft inserts",
            "performance": "mature, elegant, emotionally pressurized, no karaoke staging",
            "camera": "slow lateral tracks, profile coverage, wide face-safe frames",
            "movement": "grounded side-travel, below-shoulder arms, no random dance vocabulary",
            "edit_rhythm": "quiet verses, stronger chorus object/face alternation",
            "strengths": ["uses approved world", "supports full-song edit", "protects identity risk"],
            "risks": ["caption sync still review-only", "AI frames require optional model approval"],
        },
        {
            "id": "concept-b",
            "title": "Winter Window, Crimson Dress",
            "idea": "A colder, more graphic version built around negative space and the window as emotional pressure.",
            "palette": ["winter blue", "crimson silk", "black wood", "muted gold"],
            "setting": "bar stage reduced to silhouettes and window reflections",
            "performance": "stillness, breath, small hand releases",
            "camera": "asymmetric frames with left-side negative space",
            "movement": "minimal walking, turns and object touch only",
            "edit_rhythm": "longer holds with chorus emphasis",
            "strengths": ["readable emotion", "less motion risk"],
            "risks": ["may need more object insert coverage"],
        },
        {
            "id": "concept-c",
            "title": "Objects After Love",
            "idea": "The song is carried by bar objects, lacquer/craft inserts and withheld performance.",
            "palette": ["lacquer red", "teak brown", "amber", "smoke gray"],
            "setting": "bar details, empty glass, microphone only at ending",
            "performance": "few direct face moments, mostly profile and silhouette",
            "camera": "macro inserts and slow reveals",
            "movement": "object actions and small grounded steps",
            "edit_rhythm": "object cutaways cover low-confidence lyric regions",
            "strengths": ["face-safe", "culturally specific material world"],
            "risks": ["less performer-forward if overused"],
        },
    ]
    payload = {"project_id": project_id, "idea": idea, "concepts": concepts, "recommended": concepts[0], "status": "created"}
    write_json(paths.root / "CONCEPTS.json", payload)
    return payload


def create_storyboard_bundle(project_id: str) -> dict[str, Any]:
    paths = studio_paths(project_id)
    cards = list_storyboard_cards()
    storyboard = []
    for card in cards:
        shot = {
            "shot_id": card["shot_number"],
            "timecode": f"{card['timecode_start']} - {card['timecode_end']}",
            "lyric": card.get("song_section", ""),
            "story_purpose": card.get("purpose", ""),
            "camera": card.get("camera_movement", ""),
            "lighting": card.get("lighting", ""),
            "movement": card.get("exact_movement", ""),
            "duration": card.get("timecode_end", ""),
            "renderer": card.get("recommended_renderer", ""),
            "fallback_renderer": card.get("fallback_renderer", ""),
            "image_path": card.get("raster_path", ""),
            "image_origin": "LOCAL ASSET COMPOSITE",
            "composition_diagram": "auto diagram available from storyboard visual grammar",
            "camera_diagram": "auto camera mark/lens/movement diagram",
            "lighting_diagram": "auto key/fill/rim/practical diagram",
            "blocking_diagram": "auto performer path and eyeline diagram",
            "quality_status": "review_only",
        }
        storyboard.append(shot)
    payload = {
        "project_id": project_id,
        "shot_count": len(storyboard),
        "ai_generated_frame_count": 0,
        "composite_frame_count": len(storyboard),
        "label": "LOCAL ASSET COMPOSITE",
        "shots": storyboard,
    }
    write_json(paths.root / "STORYBOARD.json", payload)
    return payload


def create_video_sketch(project_id: str) -> dict[str, Any]:
    paths = studio_paths(project_id)
    paths.previews.mkdir(parents=True, exist_ok=True)
    source_dir = ENGINE_ROOT / "animatics" / "15"
    mapping = {
        "ANIMATIC.mp4": "CREATIVE_SKETCH.mp4",
        "ANIMATIC_WITH_CAPTIONS_SYNC_CALIBRATED_REVIEW.mp4": "CREATIVE_SKETCH_WITH_CAPTIONS.mp4",
        "ANIMATIC_REVIEW.mp4": "CREATIVE_SKETCH_REVIEW.mp4",
    }
    copied = {}
    for src_name, dst_name in mapping.items():
        src = source_dir / src_name
        dst = paths.previews / dst_name
        if src.exists():
            shutil.copy2(src, dst)
            copied[dst_name] = str(dst)
    metadata = {}
    clean = paths.previews / "CREATIVE_SKETCH.mp4"
    if clean.exists():
        try:
            metadata = probe_media(clean)
        except Exception as exc:
            metadata = {"error": type(exc).__name__, "message": str(exc)}
    payload = {
        "label": "LOCAL PREVIS VIDEO SKETCH - NOT FINAL VIDEO",
        "source": "Run 15 full-song local animatic",
        "files": copied,
        "metadata": metadata,
        "asset_urls": {
            name: f"/studio-assets/{project_id}/previews/{name}" for name in copied
        },
    }
    write_json(paths.previews / "VIDEO_SKETCH_STATUS.json", payload)
    return payload


def create_prompt_packages(project_id: str) -> dict[str, Any]:
    paths = studio_paths(project_id)
    paths.packages.mkdir(parents=True, exist_ok=True)
    storyboard = read_json(paths.root / "STORYBOARD.json", {"shots": []})
    packages = []
    for shot in storyboard.get("shots", []):
        short = f"{shot['shot_id']}: {shot.get('story_purpose') or 'cinematic Burmese bar performance'}"
        package = {
            "shot_id": shot["shot_id"],
            "renderer": shot.get("renderer") or "manual_generic_fallback",
            "fallback_renderer": shot.get("fallback_renderer") or "local_asset_composite",
            "short_director_instruction": short,
            "full_technical_prompt": (
                f"{short}. Mature solo Burmese performance in approved dark teak Finnish bar, winter window, "
                f"amber/crimson practical lighting. Camera: {shot.get('camera')}. Lighting: {shot.get('lighting')}. "
                f"Movement: {shot.get('movement')}. Natural adult proportions. No karaoke, kung fu, K-pop, TikTok."
            ),
            "negative_prompt": "karaoke, lounge singer, microphone-centered staging, martial arts, kung fu, K-pop, TikTok, fake body reshaping, child, generic Asian decor",
            "input_reference_mapping": ["approved face refs A1/A2 only when explicitly allowed", "approved wardrobe/body B", "approved bar C", "approved Burmese art E"],
            "motion_mapping": shot.get("movement", ""),
            "duration": shot.get("duration", ""),
            "identity_rules": "Use only exact approved references; no broad private folders.",
            "body_rules": "Natural adult proportions; no reshaping.",
            "privacy_state": "local package; cloud upload requires approval.",
            "likely_failures": ["caption sync unverified", "identity drift", "generic choreography"],
            "qc_scorecard": ["identity", "body realism", "Burmese cultural specificity", "caption timing", "motion realism"],
        }
        write_json(paths.packages / f"{shot['shot_id']}_PACKAGE.json", package)
        packages.append(package)
    manifest = {"project_id": project_id, "package_count": len(packages), "packages": packages}
    write_json(paths.packages / "PACKAGE_MANIFEST.json", manifest)
    return manifest


def studio_asset(project_id: str, relative_path: str) -> tuple[Path | None, int, str]:
    paths = studio_paths(project_id)
    root = paths.root.resolve()
    path = (root / relative_path).resolve()
    if not str(path).startswith(str(root)):
        return None, 403, "path traversal blocked"
    if path.suffix.lower() not in set(ALLOWED_EXTENSIONS).union({".json"}):
        return None, 403, "asset type is not allowed"
    if not path.exists() or not path.is_file():
        return None, 404, "asset not found"
    return path, 200, "ok"


def build_input_record(project_id: str, path: Path, original_name: str, sha: str) -> dict[str, Any]:
    suffix = path.suffix.lower()
    media_type = media_type_for_suffix(suffix)
    classification = classify_asset(original_name, suffix)
    metadata = {}
    if media_type in {"image", "video", "audio"}:
        try:
            metadata = probe_media(path)
        except Exception as exc:
            metadata = {"probe_error": type(exc).__name__, "message": str(exc)}
    thumb = create_thumbnail_or_waveform(project_id, path, media_type)
    return {
        "input_id": sha[:12],
        "original_name": original_name,
        "stored_name": path.name,
        "path": str(path),
        "asset_url": f"/studio-assets/{project_id}/inputs/{path.name}",
        "sha256": sha,
        "extension": suffix,
        "media_type": media_type,
        "classification": classification,
        "privacy": privacy_for_classification(classification),
        "rights": "user_supplied_needs_confirmation" if project_id != DEFAULT_PROJECT_ID else "existing_project_or_user_supplied",
        "metadata": metadata,
        "thumbnail_url": thumb.get("url", ""),
        "preview_status": thumb.get("status", "not_created"),
    }


def create_thumbnail_or_waveform(project_id: str, path: Path, media_type: str) -> dict[str, str]:
    paths = studio_paths(project_id)
    log = paths.root / "UPLOAD_MEDIA_BUILD_LOG.txt"
    stem = path.stem
    try:
        if media_type == "image":
            out = paths.thumbnails / f"{stem}.png"
            result = run_ffmpeg(["-y", "-i", str(path), "-vf", "scale=480:-1", "-frames:v", "1", str(out)], log)
            if result.returncode == 0 and out.exists():
                return {"status": "created", "url": f"/studio-assets/{project_id}/thumbnails/{out.name}"}
        if media_type == "video":
            out = paths.contact_sheets / f"{stem}.png"
            result = run_ffmpeg(["-y", "-i", str(path), "-vf", "fps=1/8,scale=240:-1,tile=3x2", "-frames:v", "1", str(out)], log)
            if result.returncode == 0 and out.exists():
                return {"status": "created", "url": f"/studio-assets/{project_id}/contact-sheets/{out.name}"}
        if media_type == "audio":
            out = paths.waveforms / f"{stem}.png"
            result = run_ffmpeg(["-y", "-i", str(path), "-filter_complex", "showwavespic=s=900x180:colors=D69B49", "-frames:v", "1", str(out)], log)
            if result.returncode == 0 and out.exists():
                return {"status": "created", "url": f"/studio-assets/{project_id}/waveforms/{out.name}"}
    except Exception as exc:
        return {"status": f"failed:{type(exc).__name__}", "url": ""}
    return {"status": "not_created", "url": ""}


def media_type_for_suffix(suffix: str) -> str:
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    if suffix in AUDIO_EXTENSIONS:
        return "audio"
    if suffix in TEXT_EXTENSIONS:
        return "text"
    if suffix == ".pdf":
        return "document"
    return "unknown"


def classify_asset(name: str, suffix: str) -> str:
    lowered = name.lower()
    if suffix in AUDIO_EXTENSIONS:
        return "music" if not any(token in lowered for token in ["voice", "vocal", "spoken"]) else "voice_reference"
    if suffix in TEXT_EXTENSIONS:
        return "lyrics"
    if suffix in VIDEO_EXTENSIONS:
        if any(token in lowered for token in ["motion", "dance", "walk", "reference"]):
            return "motion_reference"
        return "footage"
    if any(token in lowered for token in ["face", "front", "threequarter", "identity", "wife"]):
        return "performer_identity"
    if any(token in lowered for token in ["body", "wardrobe", "dress", "fullbody"]):
        return "wardrobe"
    if any(token in lowered for token in ["bar", "stage", "location", "window"]):
        return "location"
    if any(token in lowered for token in ["burmese", "art", "craft", "lacquer"]):
        return "cultural_artwork"
    if any(token in lowered for token in ["mic", "glass", "prop", "object"]):
        return "object_insert"
    return "unknown"


def privacy_for_classification(classification: str) -> str:
    if classification in {"performer_identity", "voice_reference", "body_full_body", "wardrobe"}:
        return "private_exact_asset_only"
    if classification in {"rejected", "restricted"}:
        return "restricted_blocked"
    return "local_project_asset"


def safe_project_id(value: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", value.strip().lower()).strip("-")[:80]


def sanitize_filename(value: str) -> str:
    stem = Path(value).stem
    suffix = Path(value).suffix.lower()
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip(".-")[:80] or "upload"
    return f"{safe_stem}{suffix}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _missing_inputs(counts: dict[str, int]) -> list[str]:
    missing = []
    if counts.get("music", 0) == 0:
        missing.append("No new uploaded song, using existing audio/01.mp3.")
    if counts.get("lyrics", 0) == 0:
        missing.append("No new uploaded lyrics, using existing Burmese lyric state.")
    if counts.get("performer_identity", 0) == 0:
        missing.append("No new identity upload, using approved A1/A2 references.")
    return missing


def _ensure_project_dirs(paths: StudioPaths) -> None:
    for path in paths.__dict__.values():
        path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {} if default is None else default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
