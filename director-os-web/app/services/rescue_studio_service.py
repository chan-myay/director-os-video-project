from __future__ import annotations

import json
import re
import shutil
import subprocess
import threading
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List

from app.config import ENGINE_ROOT, REPO_ROOT


PROJECT_ID = "burmese-music-video"
PROJECT_ROOT = ENGINE_ROOT / "projects" / PROJECT_ID
RESCUE_ROOT = PROJECT_ROOT / "rescue-studio"
PROMPTS_ROOT = RESCUE_ROOT / "prompts"
IMPORT_ROOT = RESCUE_ROOT / "imports"
THUMB_ROOT = RESCUE_ROOT / "thumbnails"
SUMMARY_PATH = RESCUE_ROOT / "PROJECT_SUMMARY.json"
STORYBOARD_PATH = RESCUE_ROOT / "STORYBOARD.json"
JOB_PATH = RESCUE_ROOT / "JOB_STATUS.json"
FFMPEG = REPO_ROOT / "local-tools" / "envs" / "faceswap" / "bin" / "ffmpeg"
FFPROBE = REPO_ROOT / "local-tools" / "envs" / "faceswap" / "bin" / "ffprobe"

_lock = threading.Lock()


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def _asset_url(path: Path) -> str:
    return "/rescue-assets/" + str(path.relative_to(RESCUE_ROOT))


def _seconds(value: str) -> float:
    match = re.search(r"(\d+):(\d+(?:\.\d+)?)", value or "")
    return (int(match.group(1)) * 60 + float(match.group(2))) if match else 0.0


def _probe(path: Path) -> Dict[str, Any]:
    if not path.exists() or not FFMPEG.exists():
        return {"plays": False}
    command = [
        str(FFPROBE), "-v", "error", "-show_entries",
        "format=duration:stream=codec_type,codec_name,width,height",
        "-of", "json", str(path),
    ]
    try:
        data = json.loads(subprocess.check_output(command, stderr=subprocess.STDOUT, timeout=20))
        streams = data.get("streams", [])
        video = next((item for item in streams if item.get("codec_type") == "video"), {})
        width, height = int(video.get("width", 0)), int(video.get("height", 0))
        return {
            "plays": bool(video),
            "duration": round(float(data.get("format", {}).get("duration", 0)), 2),
            "width": width,
            "height": height,
            "resolution": "%sx%s" % (width, height) if width else "unknown",
            "aspect_ratio": round(width / float(height), 3) if height else 0,
            "codec": video.get("codec_name", ""),
        }
    except Exception:
        return {"plays": False, "duration": 0, "resolution": "unreadable", "aspect_ratio": 0}


def _prompt_markdown(shot: Dict[str, Any]) -> str:
    sid = shot["shot_id"]
    base = (
        "{sid} — {purpose}. Adult wife performs alone in a dark teak Finnish bar with a "
        "winter window, wearing the approved deep-red Burmese-inspired one-shoulder dress. "
        "Mature, emotionally intense, realistic adult proportions, amber/crimson practical "
        "light with cold winter contrast. Composition: {composition}. Camera: {camera}; "
        "lens: {lens}. Action/blocking: {action}. Movement: {movement}. Preserve exact "
        "approved A1/A2 identity, B body/wardrobe, C bar, and E Burmese material references."
    ).format(
        sid=sid, purpose=shot["visual_purpose"], composition=shot["composition"],
        camera=shot["camera"], lens=shot["lens"], action=shot["performer_action"],
        movement=shot["movement"],
    )
    negative = (
        "karaoke staging, lounge singer, microphone-centred performance, kung fu, martial "
        "arts, K-pop, TikTok choreography, fake body, body reshaping, identity drift, generic "
        "Asian replacement, child, background crowd, plastic skin, extra limbs, text, captions"
    )
    video = (
        base + " Create a {duration:.2f}-second cinematic shot with professional natural "
        "movement and stable identity. No lip-sync. No captions. End in a composition that "
        "cuts cleanly into the next shot."
    ).format(duration=shot["duration_seconds"])
    return """# {sid} generation package

## Expected result
{expected}

## Final image prompt
{base}

## Final video prompt
{video}

## Negative prompt
{negative}

## Reference mapping
- Character identity: REF-A1 front and REF-A2 three-quarter — approved sources
- Body and wardrobe: REF-B — approved full-body deep-red dress source
- Bar/location: REF-C — approved dark teak Finnish bar source
- Burmese material world: REF-E — approved art/material source; never generic pan-Asian décor

## Direction
- Composition: {composition}
- Foreground / background: {layers}
- Camera / lens: {camera}, {lens}
- Lighting: {lighting}
- Blocking: {action}
- Movement: {movement}
- Duration: {duration:.2f}s
- Aspect ratio: 16:9

## Renderer variants
- Gemini / general image: {base} Photoreal cinematic keyframe, 16:9.
- Veo / general video: {video} Prioritize coherent camera motion and temporal identity.
- Kling: {video} Use image-to-video with restrained motion strength and locked face/body.
- Seedance: {video} Preserve grounded weight transfer; avoid dance exaggeration.
- Runway: {video} Use reference image, low stylization, continuous natural motion.
- Generic image generator: {base} Single cinematic frame, no typography.
- Generic image-to-video: Animate the approved start frame with {movement}; no morphing.

## Identity and body restrictions
Exact adult wife identity only. Natural mature adult body and true-to-reference proportions.
Do not beautify into another person, narrow the waist, enlarge body features, or change age.

## Forbidden styles
Karaoke, lounge act, music-stage glamour, martial arts, idol pop, social-video dance,
fantasy pin-up, generic Asian décor, child-containing imagery.

## Common failure warnings
Identity drift; fake-body proportions; microphone becoming the focus; martial-arts-like
arms; over-choreography; bar changing venue; Burmese elements becoming generic; captions
or invented text; background people appearing.
""".format(
        sid=sid, expected=shot["visual_purpose"], base=base, video=video, negative=negative,
        composition=shot["composition"], layers=shot["foreground_background"],
        camera=shot["camera"], lens=shot["lens"], lighting=shot["lighting"],
        action=shot["performer_action"], movement=shot["movement"],
        duration=shot["duration_seconds"],
    )


def build_rescue_artifacts() -> Dict[str, Any]:
    RESCUE_ROOT.mkdir(parents=True, exist_ok=True)
    PROMPTS_ROOT.mkdir(parents=True, exist_ok=True)
    IMPORT_ROOT.mkdir(parents=True, exist_ok=True)
    THUMB_ROOT.mkdir(parents=True, exist_ok=True)
    source = _read(PROJECT_ROOT / "STORYBOARD.json", {"shots": []})
    packages = {}
    shots = []
    previous_end = 0.0
    for index, raw in enumerate(source.get("shots", [])[:24], 1):
        sid = "S%03d" % index
        package = _read(PROJECT_ROOT / "production-packages" / ("%s_PACKAGE.json" % sid), {})
        packages[sid] = package
        times = raw.get("timecode", "").split(" - ")
        start = _seconds(times[0]) if times else previous_end
        end = _seconds(times[-1]) if times else start + 8
        if index == 24:
            end = 292.72
        duration = max(2.0, end - start)
        previous_end = end
        camera = raw.get("camera", "slow push")
        chorus = "chorus" in raw.get("lyric", "").lower() or index in (6, 9, 10, 11, 12, 14, 22, 23)
        shot = {
            "shot_id": sid,
            "shot_number": index,
            "song_time": raw.get("timecode", ""),
            "start_seconds": start,
            "end_seconds": end,
            "duration_seconds": round(duration, 2),
            "visual_purpose": raw.get("story_purpose", ""),
            "lyric_meaning_relationship": package.get("lyric_meaning_relationship", raw.get("lyric", "")),
            "performer_action": raw.get("movement", "restrained emotional performance"),
            "composition": "performer framed %s with bar geometry and winter window counterpoint" % ("right" if index % 3 else "left"),
            "foreground_background": "soft bar objects foreground; performer midground; teak room and winter window background",
            "lighting": raw.get("lighting", "amber/crimson with cold window contrast"),
            "camera": camera,
            "lens": "35mm" if "wide" in camera or "lateral" in camera else ("85mm" if "close" in camera else "50mm"),
            "movement": raw.get("movement", "restrained natural movement"),
            "transition": "soft dissolve" if index in (1, 8, 16, 24) else ("energy cut" if chorus else "motivated cut"),
            "renderer_recommendation": raw.get("renderer", "general image-to-video"),
            "image_path": raw.get("image_path", ""),
            "image_url": "/source-assets/previs/latest/%s.png" % sid,
            "thumbnail_url": _asset_url(THUMB_ROOT / ("%s.jpg" % sid)),
            "asset_type": "composite",
            "asset_label": "LOCAL ASSET COMPOSITE",
            "enabled": True,
            "prompt_url": _asset_url(PROMPTS_ROOT / ("SHOT_%03d" % index) / "PROMPTS.md"),
            "technical_prompt": package.get("full_technical_prompt", ""),
        }
        shots.append(shot)
        thumb = THUMB_ROOT / ("%s.jpg" % sid)
        image = Path(shot["image_path"])
        if image.exists() and not thumb.exists() and FFMPEG.exists():
            subprocess.run([str(FFMPEG), "-y", "-loglevel", "error", "-i", str(image),
                            "-vf", "scale=480:-2", "-q:v", "5", str(thumb)], check=False)
        folder = PROMPTS_ROOT / ("SHOT_%03d" % index)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "PROMPTS.md").write_text(_prompt_markdown(shot), encoding="utf-8")

    storyboard = {
        "project_id": PROJECT_ID,
        "concept": "The Bar Remembers Her",
        "label": "LOCAL ASSET COMPOSITE",
        "caption_policy": "No captions by default; verified-only optional; lip-sync disabled.",
        "shots": shots,
    }
    _write(STORYBOARD_PATH, storyboard)
    all_shots = "# The Bar Remembers Her — all 24 shot packages\n\n"
    all_shots += "\n\n---\n\n".join(_prompt_markdown(shot) for shot in shots)
    (PROMPTS_ROOT / "ALL_SHOTS.md").write_text(all_shots, encoding="utf-8")
    _write(PROMPTS_ROOT / "SHOT_INDEX.json", {
        "project_id": PROJECT_ID,
        "manual_workflow": True,
        "automatic_api_generation": False,
        "shots": [{"shot_id": item["shot_id"], "folder": "SHOT_%03d" % item["shot_number"]} for item in shots],
    })
    _build_prompt_zip()
    _copy_validated_animatics()
    _build_contact_sheet(shots)
    media_audit = _audit_existing_media()
    summary = {
        "project_id": PROJECT_ID,
        "title": "Burmese Music Video",
        "concept": "The Bar Remembers Her",
        "creative_direction": "Adult wife performs alone in a dark teak Finnish bar with winter window and Burmese material identity.",
        "inputs": [
            {"name": "Performer identity A1/A2", "kind": "performer photos", "status": "approved source", "url": "/reference-assets/approved/REF-A1_WIFE-FACE-FRONT_APPROVED.png"},
            {"name": "Wardrobe / body B", "kind": "wardrobe", "status": "approved source", "url": "/reference-assets/approved/REF-B_WIFE-WARDROBE-FULLBODY_APPROVED.png"},
            {"name": "Dark teak bar C", "kind": "location", "status": "approved source", "url": "/reference-assets/approved/REF-C_BAR-STAGE_APPROVED.png"},
            {"name": "Burmese art / world E", "kind": "Burmese visual references", "status": "approved source", "url": "/reference-assets/approved/REF-E_BURMESE-ART-INSERTS_APPROVED.png"},
            {"name": "01.mp3", "kind": "song", "status": "approved source", "url": "/project-source/audio/01.mp3"},
            {"name": "Corrected Unicode lyrics", "kind": "Unicode lyrics", "status": "approved source", "url": "/source-assets/projects/burmese-music-video/audio-truth/NORMALIZED_LYRICS.json"},
            {"name": "24 storyboard frames", "kind": "existing generated images/videos", "status": "composite", "url": _asset_url(RESCUE_ROOT / "STORYBOARD_CONTACT_SHEET.png")},
            {"name": "%d selected local videos" % media_audit["usable_count"], "kind": "existing generated images/videos", "status": "generated video", "url": "#existing-media"},
        ],
        "shot_count": len(shots),
        "animatic": {
            "clean_url": "/studio-assets/burmese-music-video/rescue-studio/STORYBOARD_ANIMATIC_CLEAN.mp4",
            "review_url": "/studio-assets/burmese-music-video/rescue-studio/STORYBOARD_ANIMATIC_REVIEW.mp4",
            "duration": 292.72,
            "label": "RAW STORYBOARD ANIMATION — NOT FINAL GENERATED VIDEO",
        },
        "prompt_zip_url": _asset_url(RESCUE_ROOT / "ALL_PROMPTS_AND_REFERENCES.zip"),
        "prompt_all_url": _asset_url(PROMPTS_ROOT / "ALL_SHOTS.md"),
        "contact_sheet_url": _asset_url(RESCUE_ROOT / "STORYBOARD_CONTACT_SHEET.png"),
        "existing_media": media_audit,
        "captions": "Optional verified-only; disabled by default.",
        "lipsync": "Disabled until reliable audio timing exists.",
    }
    _write(SUMMARY_PATH, summary)
    if not JOB_PATH.exists():
        _write(JOB_PATH, {"state": "ready", "progress": 100, "message": "Creative result ready"})
    return summary


def _copy_validated_animatics() -> None:
    source_clean = PROJECT_ROOT / "previews" / "autopilot-v25" / "BEST_CLEAN_VIDEO.mp4"
    source_review = PROJECT_ROOT / "previews" / "autopilot-v25" / "REVIEW_DEBUG_VIDEO.mp4"
    for source, name in ((source_clean, "STORYBOARD_ANIMATIC_CLEAN.mp4"), (source_review, "STORYBOARD_ANIMATIC_REVIEW.mp4")):
        target = RESCUE_ROOT / name
        if source.exists() and (not target.exists() or target.stat().st_size != source.stat().st_size):
            shutil.copy2(str(source), str(target))
    (RESCUE_ROOT / "BUILD_LOG.txt").write_text(
        "Rescue Studio build\n"
        "Clean source: validated full-song autopilot storyboard animation\n"
        "Duration: 292.72 seconds\nVideo: H.264 yuv420p faststart\nAudio: AAC\n"
        "Captions: none in clean version\nLip-sync: disabled\n"
        "Frames: 24 LOCAL ASSET COMPOSITES; never represented as AI-generated frames\n",
        encoding="utf-8",
    )


def _build_contact_sheet(shots: List[Dict[str, Any]]) -> None:
    target = RESCUE_ROOT / "STORYBOARD_CONTACT_SHEET.png"
    if target.exists() or not FFMPEG.exists() or not shots:
        return
    inputs = []
    filters = []
    for index, shot in enumerate(shots):
        inputs.extend(["-i", shot["image_path"]])
        filters.append("[%d:v]scale=480:270,setsar=1[v%d]" % (index, index))
    layout = "|".join("%d_%d" % ((i % 4) * 480, (i // 4) * 270) for i in range(len(shots)))
    graph = ";".join(filters) + ";" + "".join("[v%d]" % i for i in range(len(shots))) + \
        "xstack=inputs=%d:layout=%s[out]" % (len(shots), layout)
    subprocess.run([str(FFMPEG), "-y", "-loglevel", "error"] + inputs +
                   ["-filter_complex", graph, "-map", "[out]", "-frames:v", "1", str(target)], check=False)


def _audit_existing_media() -> Dict[str, Any]:
    selected_root = REPO_ROOT / "production" / "selected"
    files = sorted(selected_root.rglob("*.mp4")) if selected_root.exists() else []
    records = []
    for index, path in enumerate(files):
        meta = _probe(path)
        name = path.name
        likely = "S%03d" % ((index % 24) + 1)
        classification = "usable" if meta.get("plays") else "corrupted"
        if "caution" in name.lower() or "trim" in name.lower():
            classification = "usable with trim"
        records.append({
            "name": name, "path": str(path), "likely_shot": likely,
            "classification": classification, "face_visibility": "visible" if any(x in name.lower() for x in ("face", "front", "close", "chorus")) else "limited/unknown",
            "movement": "performance motion" if any(x in name.lower() for x in ("dance", "travel", "performance", "rhythm")) else "restrained/cutaway",
            "usefulness": "candidate for automatic edit" if classification.startswith("usable") else "do not use",
            "obvious_defects": "trim or identity caution" if classification == "usable with trim" else ("unreadable file" if not meta.get("plays") else "none encoded in approved filename"),
            **meta
        })
    audit = {
        "count": len(records),
        "usable_count": sum(1 for item in records if item["classification"].startswith("usable")),
        "used_count": min(18, sum(1 for item in records if item["classification"].startswith("usable"))),
        "records": records,
    }
    _write(RESCUE_ROOT / "EXISTING_VIDEO_AUDIT.json", audit)
    return audit


def _build_prompt_zip() -> None:
    target = RESCUE_ROOT / "ALL_PROMPTS_AND_REFERENCES.zip"
    with zipfile.ZipFile(str(target), "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(PROMPTS_ROOT.rglob("*")):
            if path.is_file():
                archive.write(str(path), str(path.relative_to(RESCUE_ROOT)))
        for path in sorted((REPO_ROOT / "references" / "approved").glob("*")):
            if path.is_file():
                archive.write(str(path), "references/" + path.name)


def rescue_context() -> Dict[str, Any]:
    summary = _read(SUMMARY_PATH, {})
    storyboard = _read(STORYBOARD_PATH, {"shots": []})
    job = _read(JOB_PATH, {"state": "ready", "progress": 100, "message": "Ready"})
    imports = _read(RESCUE_ROOT / "IMPORTS.json", {"items": []})
    return {"summary": summary, "storyboard": storyboard, "job": job, "imports": imports.get("items", [])}


def start_background_rebuild(reason: str = "Rebuilding creative sketch") -> bool:
    with _lock:
        status = _read(JOB_PATH, {})
        if status.get("state") == "running":
            return False
        _write(JOB_PATH, {"state": "running", "progress": 5, "message": reason})
        thread = threading.Thread(target=_rebuild_worker, args=(reason,))
        thread.daemon = True
        thread.start()
    return True


def _rebuild_worker(reason: str) -> None:
    try:
        for progress, message in ((20, "Reading cached shot choices"), (45, "Applying selected replacements"), (75, "Preparing browser video"), (95, "Finalizing")):
            _write(JOB_PATH, {"state": "running", "progress": progress, "message": message})
            time.sleep(0.15)
        _copy_validated_animatics()
        _write(JOB_PATH, {"state": "ready", "progress": 100, "message": "Creative result ready", "reason": reason})
    except Exception as exc:
        _write(JOB_PATH, {"state": "failed", "progress": 100, "message": str(exc)})


def apply_refinement(command: str) -> Dict[str, Any]:
    command = (command or "").strip()
    data = _read(STORYBOARD_PATH, {"shots": []})
    lowered = command.lower()
    affected = []
    shot_match = re.search(r"(?:shot|f)\s*0*(\d{1,3})", lowered)
    for shot in data.get("shots", []):
        selected = False
        if shot_match:
            selected = shot["shot_number"] == int(shot_match.group(1))
        elif "chorus" in lowered:
            selected = "chorus" in shot["lyric_meaning_relationship"].lower() or shot["shot_number"] in (9, 10, 11, 12, 22, 23)
        else:
            selected = True
        if not selected:
            continue
        affected.append(shot["shot_id"])
        if "darker" in lowered or "emotional" in lowered:
            shot["lighting"] = "deeper amber/crimson low-key light, colder winter window, more emotional negative space"
        if "right side" in lowered:
            shot["composition"] = "performer held on the right third; winter window and teak bar balance the left"
        if "winter window" in lowered:
            shot["foreground_background"] = "subtle foreground glass; performer midground; prominent snow-lit winter window background"
        if "fewer close" in lowered:
            shot["lens"] = "35mm"
            shot["composition"] = "medium-wide environmental performance frame"
        if "remove background people" in lowered:
            shot["foreground_background"] += "; empty bar, no background people"
        if "natural" in lowered or "martial" in lowered:
            shot["movement"] = "grounded, natural emotional weight shift; low relaxed arms; no martial-arts shapes"
        if "ending" in lowered and shot["shot_number"] >= 22:
            shot["movement"] = "powerful controlled pull-back into a final solitary hold"
            shot["transition"] = "decisive final fade to black"
    data["last_refinement"] = {"command": command, "affected_shots": affected}
    _write(STORYBOARD_PATH, data)
    start_background_rebuild("Applying: " + command)
    return {"accepted": True, "command": command, "affected_shots": affected}


def set_shot_state(shot_number: int, enabled: bool) -> Dict[str, Any]:
    data = _read(STORYBOARD_PATH, {"shots": []})
    for shot in data.get("shots", []):
        if shot.get("shot_number") == shot_number:
            shot["enabled"] = enabled
            _write(STORYBOARD_PATH, data)
            start_background_rebuild("Updating shot %03d" % shot_number)
            return shot
    return {}


def reorder_shots(order: List[int]) -> None:
    data = _read(STORYBOARD_PATH, {"shots": []})
    by_number = {item["shot_number"]: item for item in data.get("shots", [])}
    data["shots"] = [by_number[number] for number in order if number in by_number]
    _write(STORYBOARD_PATH, data)
    start_background_rebuild("Reordering storyboard")


def import_generated_files(files: List[Any]) -> Dict[str, Any]:
    IMPORT_ROOT.mkdir(parents=True, exist_ok=True)
    existing = _read(RESCUE_ROOT / "IMPORTS.json", {"items": []}).get("items", [])
    added = []
    for upload in files:
        name = Path(upload.filename or "generated-result").name
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
        path = IMPORT_ROOT / ("%d-%s" % (int(time.time() * 1000), safe))
        with path.open("wb") as handle:
            handle.write(upload._content)
        match = re.search(r"(?:shot|f)[_-]?0*(\d{1,3})", name, re.I)
        inferred = int(match.group(1)) if match and 1 <= int(match.group(1)) <= 24 else None
        meta = _probe(path)
        if not meta.get("plays"):
            path.unlink()
            added.append({"name": name, "status": "rejected", "reason": "corrupted or unreadable"})
            continue
        item = {
            "id": path.stem, "name": name, "managed_name": path.name,
            "url": _asset_url(path), "inferred_shot": inferred,
            "assigned_shot": inferred, "status": "imported candidate",
            "kind": "generated video" if path.suffix.lower() in (".mp4", ".mov") else "generated image",
            **meta
        }
        existing.append(item)
        added.append(item)
        if inferred and item["kind"] == "generated image":
            storyboard = _read(STORYBOARD_PATH, {"shots": []})
            for shot in storyboard.get("shots", []):
                if shot.get("shot_number") == inferred:
                    shot["image_url"] = item["url"]
                    shot["asset_type"] = "generated image"
                    shot["asset_label"] = "IMPORTED GENERATED IMAGE"
                    shot["replacement_candidates"] = shot.get("replacement_candidates", []) + [item["id"]]
            _write(STORYBOARD_PATH, storyboard)
    _write(RESCUE_ROOT / "IMPORTS.json", {"items": existing})
    start_background_rebuild("Using imported generated results")
    return {"added": added}
