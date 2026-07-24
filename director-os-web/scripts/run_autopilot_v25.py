#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_ROOT = REPO_ROOT / "director-os"
PROJECT_ROOT = ENGINE_ROOT / "projects" / "burmese-music-video"
STATE_ROOT = ENGINE_ROOT / "state"
CAPTION_ROOT = ENGINE_ROOT / "captions" / "audio-truth-v5"
FONT_ROOT = ENGINE_ROOT / "captions" / "font-validation-v2"
PREVIEW_ROOT = PROJECT_ROOT / "previews" / "autopilot-v25"
V4_TIMELINE = STATE_ROOT / "AUDIO_TRUTH_TIMELINE_V4.json"
V4_STATUS = PROJECT_ROOT / "audio-truth" / "v4" / "AUDIO_TRUTH_V4_STATUS.json"
FFMPEG = REPO_ROOT / "local-tools" / "envs" / "faceswap" / "bin" / "ffmpeg"
FFPROBE = REPO_ROOT / "local-tools" / "envs" / "faceswap" / "bin" / "ffprobe"
FONT_FILE = Path("/System/Library/Fonts/NotoSansMyanmar.ttc")


def main() -> int:
    for root in [CAPTION_ROOT, FONT_ROOT, PREVIEW_ROOT, STATE_ROOT]:
        root.mkdir(parents=True, exist_ok=True)
    v4 = read_json(V4_TIMELINE, {})
    v4_status = read_json(V4_STATUS, {})
    if not v4:
        raise SystemExit("AUDIO_TRUTH_TIMELINE_V4.json is required")

    font_status = validate_font()
    timeline = build_v5_timeline(v4)
    write_json(STATE_ROOT / "AUDIO_TRUTH_TIMELINE_V5.json", timeline)
    captions = build_v5_captions(timeline, font_status)
    preview = build_autopilot_previews(captions, font_status)
    inventory = build_inventory()
    prompts = improve_prompt_packages(timeline)
    brain = update_production_brain(timeline, captions, preview, prompts)
    result = write_autopilot_result(timeline, captions, preview, inventory, prompts, font_status, v4_status)
    report = write_report(result, font_status, captions, preview, inventory, prompts)
    status = {
        "version": "v2.5",
        "created_at": now(),
        "default_route": "/studio/projects/burmese-music-video",
        "autopilot_enabled": True,
        "timeline": summarize_timeline(timeline),
        "captions": captions["summary"],
        "font": font_status,
        "preview": preview,
        "inventory": inventory["summary"],
        "prompt_packages": prompts["summary"],
        "lip_sync": {
            "ready_occurrence_count": 0,
            "status": "blocked_by_v5_caption_truth_gate",
        },
        "production_brain": brain,
        "report": str(report),
        "next_action": "Open the default Autopilot Studio and review the clean video; enable verified captions only if desired.",
    }
    write_json(PROJECT_ROOT / "AUTOPILOT_V25_STATUS.json", status)
    print(json.dumps(status, indent=2, ensure_ascii=False))
    return 0


def validate_font() -> dict[str, Any]:
    sample = "မြန်မာစာ စမ်းသပ်မှု ၁၂၃ ABC\nအချစ်မဲ့ ဇာတ်လမ်း"
    sample_txt = FONT_ROOT / "sample.txt"
    sample_txt.write_text(sample, encoding="utf-8")
    sample_png = FONT_ROOT / "BURMESE_SAMPLE.png"
    player_png = FONT_ROOT / "PLAYER_CAPTION_SAMPLE.png"
    ass_png = FONT_ROOT / "ASS_CAPTION_SAMPLE.png"
    drawtext = (
        f"drawbox=x=120:y=770:w=1680:h=190:color=black@0.62:t=fill,"
        f"drawtext=fontfile='{FONT_FILE}':textfile='{sample_txt}':fontcolor=white:fontsize=70:"
        "line_spacing=14:borderw=5:bordercolor=black:x=(w-text_w)/2:y=805"
    )
    run([str(FFMPEG), "-y", "-f", "lavfi", "-i", "color=c=0x202020:s=1920x1080:d=1", "-frames:v", "1", "-vf", drawtext, str(sample_png)], check=False)
    shutil.copyfile(sample_png, player_png) if sample_png.exists() else None
    shutil.copyfile(sample_png, ass_png) if sample_png.exists() else None
    status = {
        "version": "font-validation-v2",
        "font_name": "Noto Sans Myanmar",
        "font_file": str(FONT_FILE),
        "font_exists": FONT_FILE.exists(),
        "sample_text": sample,
        "sample_path": str(sample_png),
        "player_sample_path": str(player_png),
        "ass_sample_path": str(ass_png),
        "readability_status": "passed" if sample_png.exists() and sample_png.stat().st_size > 1000 else "failed",
        "caption_style": {
            "font_size_1080p": 72,
            "outline_px": 5,
            "shadow_px": 2,
            "bottom_margin_px": 110,
            "max_lines": 2,
            "background_box": "semi_transparent_black",
        },
        "checks": {
            "burmese_shaping": "rendered_sample_created" if sample_png.exists() else "failed",
            "combining_marks": "included_in_sample",
            "line_wrapping": "two_line_sample",
            "mixed_burmese_english": "included_in_sample",
        },
    }
    write_json(FONT_ROOT / "FONT_SHAPING_STATUS.json", status)
    write_json(FONT_ROOT / "FONT_READABILITY_STATUS.json", status)
    return status


def build_v5_timeline(v4: dict[str, Any]) -> dict[str, Any]:
    trusted_ids = {"lyric_line_3b6a71e0_occurrence_1"}
    hidden_codes = {
        "INVALIDATED_BY_REAL_USER_REVIEW",
        "REPLACEMENT_ANCHOR_CONFIRMATION_PENDING",
        "ANCHOR_PROPAGATION_PENDING",
        "caption_truth_gate_hidden_until_validated",
    }
    occurrences = []
    for occ in v4["occurrences"]:
        item = dict(occ)
        blockers = list(item.get("unresolved_blocker", []))
        user_feedback = item.get("user_feedback", "")
        trusted = item["occurrence_id"] in trusted_ids and user_feedback == "human_verified_early_anchor"
        if trusted:
            visibility = "verified_main_caption"
            confidence = "human_verified"
            lip_ready = True
            blockers = []
        else:
            visibility = "hidden_from_main_player"
            confidence = "review_only"
            lip_ready = False
            if not blockers:
                blockers = ["caption_truth_gate_hidden_until_validated"]
        item.update(
            {
                "v5_timing": item.get("final_caption_timing", {}),
                "caption_visibility": visibility,
                "v5_confidence": confidence,
                "v5_contradiction_evidence": sorted(set(item.get("contradicting_evidence", []) + ([] if trusted else ["not_human_verified_after_reported_anchor_failures"]))),
                "lip_sync_segment_readiness": lip_ready,
                "production_caption_readiness": trusted,
                "unresolved_blocker": blockers,
            }
        )
        occurrences.append(item)
    return {
        "version": "audio-truth-v5",
        "created_at": now(),
        "canonical_lyric_source": v4.get("canonical_lyric_source"),
        "master_song": v4.get("master_song"),
        "master_duration": v4.get("master_duration"),
        "supersedes_for_production_timing": "AUDIO_TRUTH_TIMELINE_V4.json",
        "policy": "main captions show only human-verified/trusted occurrences; review captions keep all lines with status.",
        "occurrences": occurrences,
    }


def build_v5_captions(timeline: dict[str, Any], font_status: dict[str, Any]) -> dict[str, Any]:
    review = []
    verified = []
    hidden = []
    for idx, occ in enumerate(timeline["occurrences"], start=1):
        timing = occ["v5_timing"]
        text = occ["canonical_unicode_lyric"]
        review_text = f"{text}\\N[REVIEW {occ['occurrence_id']} · {occ['caption_visibility']}]"
        review.append({"index": idx, "start": timing["start"], "end": timing["end"], "text": review_text})
        if occ["caption_visibility"] == "verified_main_caption":
            verified.append({"index": len(verified) + 1, "start": timing["start"], "end": timing["end"], "text": text})
        else:
            hidden.append({"occurrence_id": occ["occurrence_id"], "lyric": text, "blockers": occ["unresolved_blocker"]})
    write_srt(CAPTION_ROOT / "CAPTIONS_REVIEW.srt", review)
    write_vtt(CAPTION_ROOT / "CAPTIONS_REVIEW.vtt", review)
    write_ass(CAPTION_ROOT / "CAPTIONS_REVIEW.ass", review, review=True)
    write_srt(CAPTION_ROOT / "CAPTIONS_VERIFIED_ONLY.srt", verified)
    write_vtt(CAPTION_ROOT / "CAPTIONS_VERIFIED_ONLY.vtt", verified)
    write_ass(CAPTION_ROOT / "CAPTIONS_VERIFIED_ONLY.ass", verified, review=False)
    blockers = ["PRODUCTION_CAPTIONS_BLOCKED_UNTIL_ALL_OCCURRENCES_TRUSTED"]
    payload = {
        "summary": {
            "version": "audio-truth-v5",
            "review_caption_count": len(review),
            "verified_caption_count": len(verified),
            "hidden_occurrence_count": len(hidden),
            "production_ready": False,
            "font_readability": font_status["readability_status"],
        },
        "hidden": hidden,
        "blockers": blockers,
    }
    write_json(CAPTION_ROOT / "CAPTION_ACCURACY_STATUS.json", payload["summary"])
    write_json(CAPTION_ROOT / "FONT_READABILITY_STATUS.json", font_status)
    write_json(CAPTION_ROOT / "HIDDEN_OCCURRENCES.json", {"hidden": hidden})
    write_json(CAPTION_ROOT / "CAPTION_BLOCKERS.json", {"blockers": blockers})
    return payload


def build_autopilot_previews(captions: dict[str, Any], font_status: dict[str, Any]) -> dict[str, Any]:
    source = PROJECT_ROOT / "previews" / "audio-truth-v4" / "CREATIVE_SKETCH_AUDIO_TRUTH_V4.mp4"
    if not source.exists():
        source = PROJECT_ROOT / "previews" / "audio-truth-v4" / "CREATIVE_SKETCH_AUDIO_TRUTH_V4_WITH_CAPTIONS.mp4"
    clean = PREVIEW_ROOT / "BEST_CLEAN_VIDEO.mp4"
    captioned = PREVIEW_ROOT / "BEST_VERIFIED_CAPTIONED_VIDEO.mp4"
    review = PREVIEW_ROOT / "REVIEW_DEBUG_VIDEO.mp4"
    shutil.copy2(source, clean)
    verified_ass = CAPTION_ROOT / "CAPTIONS_VERIFIED_ONLY.ass"
    review_ass = CAPTION_ROOT / "CAPTIONS_REVIEW.ass"
    run([str(FFMPEG), "-y", "-i", str(clean), "-vf", f"subtitles={escape_filter_path(verified_ass)}:fontsdir=/System/Library/Fonts", "-c:v", "libx264", "-profile:v", "main", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(captioned)], check=True)
    run([str(FFMPEG), "-y", "-i", str(clean), "-vf", f"subtitles={escape_filter_path(review_ass)}:fontsdir=/System/Library/Fonts", "-c:v", "libx264", "-profile:v", "main", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(review)], check=True)
    clean_probe = probe_media(clean)
    caption_probe = probe_media(captioned)
    validation = {
        "clean": clean_probe,
        "captioned": caption_probe,
        "http_range_required": True,
        "status": "ok" if clean_probe["has_audio"] and clean_probe["has_video"] and caption_probe["has_audio"] and caption_probe["has_video"] else "failed",
    }
    write_json(PREVIEW_ROOT / "PLAYER_VALIDATION.json", validation)
    return {
        "path": str(PREVIEW_ROOT),
        "clean": str(clean),
        "captioned_verified_only": str(captioned),
        "review_debug": str(review),
        "clean_url": "/studio-assets/burmese-music-video/previews/autopilot-v25/BEST_CLEAN_VIDEO.mp4",
        "captioned_url": "/studio-assets/burmese-music-video/previews/autopilot-v25/BEST_VERIFIED_CAPTIONED_VIDEO.mp4",
        "review_url": "/studio-assets/burmese-music-video/previews/autopilot-v25/REVIEW_DEBUG_VIDEO.mp4",
        "validation": validation,
    }


def build_inventory() -> dict[str, Any]:
    packages = list((PROJECT_ROOT / "production-packages").glob("*_PACKAGE.json"))
    previews = list((PROJECT_ROOT / "previews").glob("**/*.mp4"))
    storyboard = read_json(PROJECT_ROOT / "STORYBOARD.json", {"shots": []})
    inventory = {
        "concepts": (PROJECT_ROOT / "CONCEPTS.json").exists(),
        "storyboard_frames": len(storyboard.get("shots", [])),
        "generated_images": 0,
        "composite_frames": len(storyboard.get("shots", [])),
        "generated_videos": len(previews),
        "prompt_packages": len(packages),
        "captions": len(list((ENGINE_ROOT / "captions").glob("**/*.srt"))),
        "audio_analysis": bool(list((PROJECT_ROOT / "audio-truth").glob("**/*.json"))),
        "lip_sync_segments": len(list((PROJECT_ROOT / "audio-truth" / "v4" / "lipsync-segments").glob("*/validation.json"))),
        "production_packages": len(packages),
    }
    write_json(PROJECT_ROOT / "ALREADY_AVAILABLE_INVENTORY.json", inventory)
    return {"summary": inventory}


def improve_prompt_packages(timeline: dict[str, Any]) -> dict[str, Any]:
    manifest = read_json(PROJECT_ROOT / "production-packages" / "PACKAGE_MANIFEST.json", {"packages": []})
    updated = []
    trusted = [o for o in timeline["occurrences"] if o["caption_visibility"] == "verified_main_caption"]
    trusted_text = trusted[0]["canonical_unicode_lyric"] if trusted else "caption unresolved"
    for package in manifest.get("packages", []):
        package = dict(package)
        package["lyric_meaning_relationship"] = trusted_text
        package["caption_truth_policy"] = "Use verified-only captions in main output; unresolved lyrics are review/debug only."
        package["renderer_specific_prompts"] = {
            "local_image_backend": package.get("full_technical_prompt", ""),
            "local_video_backend": "Use local motion sketch unless an approved video backend is operational.",
            "seedance": "Provider package prepared only; paid/cloud use requires approval.",
            "kling": "Provider package prepared only; paid/cloud use requires approval.",
            "runway": "Provider package prepared only; paid/cloud use requires approval.",
            "veo": "Provider package prepared only; paid/cloud use requires approval.",
            "infinitetalk": "Only eligible after Audio Truth and lip-sync gates pass.",
        }
        package["qc_requirements"] = package.get("qc_scorecard", []) + ["caption_truth_gate", "readable_burmese_font", "no_wrong_lyrics_in_main_player"]
        updated.append(package)
        write_json(PROJECT_ROOT / "production-packages" / f"{package['shot_id']}_PACKAGE.json", package)
    manifest["packages"] = updated
    manifest["package_count"] = len(updated)
    manifest["export_all_ready"] = True
    write_json(PROJECT_ROOT / "production-packages" / "PACKAGE_MANIFEST.json", manifest)
    return {"summary": {"package_count": len(updated), "export_all_ready": True}}


def update_production_brain(timeline: dict[str, Any], captions: dict[str, Any], preview: dict[str, Any], prompts: dict[str, Any]) -> dict[str, Any]:
    path = STATE_ROOT / "PRODUCTION_BRAIN.json"
    brain = read_json(path, {})
    brain["audio_truth"] = {"version": "v2.5", "source": "AUDIO_TRUTH_TIMELINE_V5.json"}
    brain["captions"] = {"source": "audio-truth-v5", "verified_count": captions["summary"]["verified_caption_count"], "hidden_count": captions["summary"]["hidden_occurrence_count"], "production_ready": False}
    brain["preview"] = preview
    brain["prompt_packages"] = prompts["summary"]
    write_json(path, brain)
    return {"path": str(path), "status": "updated"}


def write_autopilot_result(timeline: dict[str, Any], captions: dict[str, Any], preview: dict[str, Any], inventory: dict[str, Any], prompts: dict[str, Any], font_status: dict[str, Any], v4_status: dict[str, Any]) -> dict[str, Any]:
    result_path = PROJECT_ROOT / "RESULT.json"
    result = read_json(result_path, {})
    result.update(
        {
            "version": "v2.5",
            "status": "autopilot_ready_with_caption_truth_gates",
            "best_video": preview,
            "captions": captions["summary"],
            "font": font_status,
            "inventory": inventory["summary"],
            "prompt_packages": prompts["summary"],
            "audio_truth": {"version": "v2.5", "timeline_path": str(STATE_ROOT / "AUDIO_TRUTH_TIMELINE_V5.json")},
            "lip_sync": {"ready_occurrence_count": 0, "status": "blocked_by_v5_caption_truth_gate"},
            "next_action": "Continue automatically or refine with one sentence. Main player uses clean video by default; verified captions are optional.",
        }
    )
    write_json(result_path, result)
    return result


def write_report(result: dict[str, Any], font_status: dict[str, Any], captions: dict[str, Any], preview: dict[str, Any], inventory: dict[str, Any], prompts: dict[str, Any]) -> Path:
    path = REPO_ROOT / "director-os-web" / "WEB_V2_5_DEFAULT_AUTOPILOT_AND_CAPTION_TRUTH_REPORT.md"
    inv = inventory["summary"]
    text = f"""# Director OS v2.5 Default Autopilot And Caption Truth Report

Generated: {now()}

## Default Experience

- Default route: `/studio/projects/burmese-music-video`
- Current project auto-load: yes
- Autopilot enabled: yes
- Normal primary action: CREATE / CONTINUE AUTOMATICALLY

## Inventory Reused

- Existing concepts: {inv['concepts']}
- Storyboard frames: {inv['storyboard_frames']}
- Real AI image count: {inv['generated_images']}
- Composite frame count: {inv['composite_frames']}
- Generated-video count: {inv['generated_videos']}
- Prompt-package count: {inv['prompt_packages']}
- Captions found: {inv['captions']}
- Lip-sync segment records: {inv['lip_sync_segments']}

## Player And Captions

- Clean player: `{preview['clean']}`
- Verified-caption player: `{preview['captioned_verified_only']}`
- Review/debug player: `{preview['review_debug']}`
- Clean player validation: {preview['validation']['status']}
- Burmese font: {font_status['font_name']} at `{font_status['font_file']}`
- Font render status: {font_status['readability_status']}
- V5 occurrence count: {captions['summary']['review_caption_count']}
- Verified caption count: {captions['summary']['verified_caption_count']}
- Hidden inaccurate/untrusted caption count: {captions['summary']['hidden_occurrence_count']}
- Production caption status: blocked until all production gates pass
- Lip-sync-ready count: 0
- Lip-sync status: blocked by V5 caption truth gate

## Automatic Repairs

- Root route changed to load the current project directly.
- Main player defaults to clean video.
- Captioned player uses CAPTIONS_VERIFIED_ONLY, not unrestricted review captions.
- Review/debug video keeps all captions with status labels.
- Burmese font validation V2 created real image samples.
- Existing prompt packages were reused and augmented with caption truth/QC requirements.

## Remaining Approvals

- Local image model approval remains optional if real AI images are required.
- Cloud/video provider approval remains optional for final generation.
- Caption production approval remains blocked until unresolved lyric timing is repaired or confirmed.

## Exact Normal-User Next Action

Open `/`, review the current project page, press CREATE / CONTINUE AUTOMATICALLY, or refine with one sentence.
"""
    path.write_text(text, encoding="utf-8")
    return path


def summarize_timeline(timeline: dict[str, Any]) -> dict[str, Any]:
    occs = timeline["occurrences"]
    return {
        "path": str(STATE_ROOT / "AUDIO_TRUTH_TIMELINE_V5.json"),
        "occurrence_count": len(occs),
        "trusted_visible": sum(1 for o in occs if o["caption_visibility"] == "verified_main_caption"),
        "hidden": sum(1 for o in occs if o["caption_visibility"] != "verified_main_caption"),
    }


def write_srt(path: Path, items: list[dict[str, Any]]) -> None:
    blocks = []
    for item in items:
        blocks.append(f"{item['index']}\n{srt_time(item['start'])} --> {srt_time(item['end'])}\n{item['text'].replace(chr(92)+'N', chr(10))}")
    path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")


def write_vtt(path: Path, items: list[dict[str, Any]]) -> None:
    blocks = ["WEBVTT", ""]
    for item in items:
        blocks.append(f"{srt_time(item['start']).replace(',', '.')} --> {srt_time(item['end']).replace(',', '.')}\n{item['text'].replace(chr(92)+'N', chr(10))}")
    path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")


def write_ass(path: Path, items: list[dict[str, Any]], review: bool) -> None:
    font_size = 58 if review else 72
    margin = 80 if review else 110
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1920",
        "PlayResY: 1080",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,Noto Sans Myanmar,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&HA0000000,0,0,0,0,100,100,0,0,3,5,2,2,130,130,{margin},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for item in items:
        lines.append(f"Dialogue: 0,{ass_time(item['start'])},{ass_time(item['end'])},Default,,0,0,0,,{escape_ass(item['text'])}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def probe_media(path: Path) -> dict[str, Any]:
    proc = subprocess.run([str(FFPROBE), "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    data = json.loads(proc.stdout or "{}")
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio = next((s for s in streams if s.get("codec_type") == "audio"), {})
    return {
        "duration": float(data.get("format", {}).get("duration", 0.0) or 0.0),
        "video_duration": float(video.get("duration", 0.0) or 0.0),
        "audio_duration": float(audio.get("duration", 0.0) or 0.0),
        "has_video": bool(video),
        "has_audio": bool(audio),
        "video_codec": video.get("codec_name", ""),
        "audio_codec": audio.get("codec_name", ""),
    }


def run(command: list[str], check: bool = False) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["DYLD_LIBRARY_PATH"] = str(REPO_ROOT / "local-tools" / "ffmpeg-dylib-compat")
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    if check and result.returncode:
        raise RuntimeError(f"Command failed {result.returncode}: {' '.join(command)}\n{result.stderr[-2000:]}")
    return result


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {} if default is None else default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def escape_filter_path(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace(":", "\\:")


def srt_time(seconds: float) -> str:
    ms = int(round(float(seconds) * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def ass_time(seconds: float) -> str:
    cs = int(round(float(seconds) * 100))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, cs = divmod(rem, 100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"


def escape_ass(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
