from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import zlib
from pathlib import Path
from typing import Any

from app.config import ENGINE_ROOT, REPO_ROOT
from app.services.latest_safe_animatic_service import latest_safe_animatic_context
from app.system_tools.binary_discovery import discover_binary
from app.system_tools.ffmpeg_service import probe_media, run_ffmpeg


PROJECT_ID = "burmese-music-video"
PROJECT_ROOT = ENGINE_ROOT / "projects" / PROJECT_ID
AUDIO_TRUTH_ROOT = PROJECT_ROOT / "audio-truth"
STATE_ROOT = ENGINE_ROOT / "state"
CAPTION_ROOT = ENGINE_ROOT / "captions" / "audio-truth-v1"
PREVIEW_ROOT = PROJECT_ROOT / "previews" / "audio-truth-v1"
MASTER_AUDIO = REPO_ROOT / "audio" / "01.mp3"
BURMESE_RE = re.compile(r"[\u1000-\u109f]")


def run_audio_truth_engine() -> dict[str, Any]:
    audit = audit_lyric_sources()
    canonical = select_canonical_lyric(audit)
    phrases = normalize_canonical_lyrics(canonical)
    bundle = audio_model_bundle_status()
    stems = prepare_vocal_separation(bundle)
    asr = run_asr_ensemble_status(bundle, stems)
    timeline = build_audio_truth_timeline(canonical, phrases, bundle, stems, asr)
    verification = verify_lyrics(canonical, phrases, timeline)
    meaning = build_meaning_performance_map(timeline)
    captions = rebuild_audio_truth_captions(timeline, verification)
    lipsync = build_lipsync_segments(timeline)
    preview = build_audio_truth_video_sketch(captions, timeline)
    brain = update_production_brain_audio_truth(timeline, meaning, captions, lipsync)
    status = {
        "project_id": PROJECT_ID,
        "canonical_lyric_source": canonical,
        "model_bundle": bundle,
        "vocal_separation": stems,
        "asr": asr,
        "timeline": {
            "path": str(STATE_ROOT / "AUDIO_TRUTH_TIMELINE.json"),
            "occurrence_count": len(timeline["occurrences"]),
            "high_confidence": sum(1 for item in timeline["occurrences"] if item["status"] == "aligned_high_confidence"),
            "medium_confidence": sum(1 for item in timeline["occurrences"] if item["status"] == "aligned_medium_confidence"),
            "needs_review": sum(1 for item in timeline["occurrences"] if item["status"] == "needs_targeted_review"),
            "blocked": sum(1 for item in timeline["occurrences"] if item["status"] in {"alignment_failed", "needs_audio_model_approval"}),
        },
        "verification": verification,
        "meaning": {"path": str(STATE_ROOT / "SONG_MEANING_PERFORMANCE_MAP.json"), "phrase_count": len(meaning["phrases"])},
        "captions": captions,
        "lipsync": lipsync,
        "preview": preview,
        "production_brain": brain,
        "next_action": _next_action(bundle, timeline, verification),
    }
    write_json(AUDIO_TRUTH_ROOT / "AUDIO_TRUTH_STATUS.json", status)
    return status


def audio_truth_status() -> dict[str, Any]:
    v4_status = read_json(AUDIO_TRUTH_ROOT / "v4" / "AUDIO_TRUTH_V4_STATUS.json", {})
    if v4_status:
        return v4_status
    v3_status = read_json(AUDIO_TRUTH_ROOT / "v3" / "AUDIO_TRUTH_V3_STATUS.json", {})
    if v3_status:
        return v3_status
    v2_status = read_json(AUDIO_TRUTH_ROOT / "v2" / "AUDIO_TRUTH_V2_STATUS.json", {})
    if v2_status:
        return v2_status
    status = read_json(AUDIO_TRUTH_ROOT / "AUDIO_TRUTH_STATUS.json", {})
    if status:
        return status
    return run_audio_truth_engine()


def run_audio_truth_v23() -> dict[str, Any]:
    script = REPO_ROOT / "director-os-web" / "scripts" / "run_audio_truth_v23.py"
    python = REPO_ROOT / ".venvs" / "audio-truth" / "bin" / "python"
    env = os.environ.copy()
    env.update(
        {
            "HF_HOME": str(REPO_ROOT / "local-models" / "audio-truth" / "hf"),
            "HF_HUB_CACHE": str(REPO_ROOT / "local-models" / "audio-truth" / "hf" / "hub"),
            "TRANSFORMERS_CACHE": str(REPO_ROOT / "local-models" / "audio-truth" / "hf" / "transformers"),
            "PYTHONNOUSERSITE": "1",
            "TOKENIZERS_PARALLELISM": "false",
        }
    )
    log_path = AUDIO_TRUTH_ROOT / "v2" / "RUN_V23.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run([str(python), str(script)], cwd=REPO_ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    log_path.write_text(proc.stdout or "", encoding="utf-8")
    status = read_json(AUDIO_TRUTH_ROOT / "v2" / "AUDIO_TRUTH_V2_STATUS.json", {})
    if proc.returncode != 0:
        status = status or {}
        status["status"] = "failed"
        status["error"] = f"Audio Truth v2.3 runner exited {proc.returncode}"
        status["log"] = str(log_path)
        write_json(AUDIO_TRUTH_ROOT / "v2" / "AUDIO_TRUTH_V2_STATUS.json", status)
    return status


def run_audio_truth_v24() -> dict[str, Any]:
    script = REPO_ROOT / "director-os-web" / "scripts" / "run_audio_truth_v24.py"
    python = REPO_ROOT / ".venvs" / "audio-truth" / "bin" / "python"
    log_path = AUDIO_TRUTH_ROOT / "v3" / "RUN_V24.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run([str(python), str(script)], cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    log_path.write_text(proc.stdout or "", encoding="utf-8")
    status = read_json(AUDIO_TRUTH_ROOT / "v3" / "AUDIO_TRUTH_V3_STATUS.json", {})
    if proc.returncode != 0:
        status = status or {}
        status["status"] = "failed"
        status["error"] = f"Audio Truth v2.4 runner exited {proc.returncode}"
        status["log"] = str(log_path)
        write_json(AUDIO_TRUTH_ROOT / "v3" / "AUDIO_TRUTH_V3_STATUS.json", status)
    return status


def run_audio_truth_v241() -> dict[str, Any]:
    python = REPO_ROOT / ".venvs" / "audio-truth" / "bin" / "python"
    log_path = AUDIO_TRUTH_ROOT / "v4" / "RUN_V241.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    command = [str(python), str(REPO_ROOT / "director-os-web" / "scripts" / "run_audio_truth_v241.py")]
    result = subprocess.run(command, cwd=str(REPO_ROOT), capture_output=True, text=True, check=False)
    log_path.write_text(result.stdout + "\n--- STDERR ---\n" + result.stderr, encoding="utf-8")
    status = read_json(AUDIO_TRUTH_ROOT / "v4" / "AUDIO_TRUTH_V4_STATUS.json", {})
    if result.returncode != 0:
        status = {
            "version": "v2.4.1",
            "status": "failed",
            "returncode": result.returncode,
            "log": str(log_path),
            "error": result.stderr[-2000:],
        }
        write_json(AUDIO_TRUTH_ROOT / "v4" / "AUDIO_TRUTH_V4_STATUS.json", status)
    return status


def audit_lyric_sources() -> dict[str, Any]:
    candidates = []
    roots = [REPO_ROOT / "lyrics", ENGINE_ROOT, PROJECT_ROOT / "inputs", REPO_ROOT / "output"]
    suffixes = {".txt", ".srt", ".vtt", ".ass", ".md", ".json"}
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in suffixes:
                continue
            if "node_modules" in path.parts or "__pycache__" in path.parts:
                continue
            record = lyric_candidate_record(path)
            if record["has_burmese"] or "lyric" in path.name.lower() or "caption" in path.name.lower():
                candidates.append(record)
    newest_unicode = max((c for c in candidates if c["encoding_class"] == "unicode" and c["lyric_phrase_count"] >= 8), key=lambda c: c["modified_time"], default=None)
    audit = {
        "created_by": "Director OS v2.2 audio truth engine",
        "candidate_count": len(candidates),
        "candidates": sorted(candidates, key=lambda item: item["modified_time"], reverse=True),
        "newest_valid_unicode_candidate": newest_unicode,
        "explicit_stale_check": {
            "path": str(PROJECT_ROOT / "inputs" / "51b07bfca4c4-Zawgyi.txt"),
            "status": "stale_history_if_canonical_unicode_is_newer",
        },
    }
    write_json(STATE_ROOT / "LYRIC_SOURCE_AUDIT.json", audit)
    return audit


def lyric_candidate_record(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    lyric_lines = [line for line in lines if line_category(line) == "lyric"]
    section_lines = [line for line in lines if line_category(line) != "lyric"]
    stat = path.stat()
    encoding_class, confidence = detect_encoding(text)
    referenced = str(path) in json.dumps(read_json(STATE_ROOT / "PRODUCTION_BRAIN.json", {}), ensure_ascii=False)
    return {
        "path": str(path),
        "filename": path.name,
        "modified_time": stat.st_mtime,
        "modified_time_iso": _iso_from_mtime(stat.st_mtime),
        "sha256": sha256_file(path),
        "encoding_class": encoding_class,
        "encoding_confidence": confidence,
        "line_count": len(lines),
        "lyric_phrase_count": len(lyric_lines),
        "title_credit_section_count": len(section_lines),
        "has_burmese": bool(BURMESE_RE.search(text)),
        "similarity_to_current_brain": similarity_to_brain(lyric_lines),
        "appears_manually_edited": appears_manually_edited(path, text),
        "referenced_by_current_production_brain": referenced,
        "used_by_studio_v21": str(path).startswith(str(PROJECT_ROOT / "inputs")),
        "sample": "\n".join(lines[:4]),
    }


def select_canonical_lyric(audit: dict[str, Any]) -> dict[str, Any]:
    candidates = audit.get("candidates", [])
    unicode_candidates = [
        c for c in candidates
        if c["encoding_class"] == "unicode"
        and c["lyric_phrase_count"] >= 8
        and "/lyrics/" in c["path"]
    ]
    if unicode_candidates:
        selected = max(unicode_candidates, key=lambda c: (c["modified_time"], c["appears_manually_edited"]))
        status = "selected_newest_valid_manual_unicode"
    else:
        selected = audit.get("newest_valid_unicode_candidate") or (candidates[0] if candidates else {})
        status = "ambiguous_needs_comparison_approval" if candidates else "missing"
    stale_by_path = {c["path"]: c for c in candidates if c["path"].endswith("51b07bfca4c4-Zawgyi.txt")}
    stale = list(stale_by_path.values())
    canonical = {
        "status": status,
        "selected": selected,
        "encoding": selected.get("encoding_class", "unknown"),
        "previous_sources": [
            {
                "path": item["path"],
                "status": "superseded_stale_retained_for_history" if item["path"] != selected.get("path") else "canonical",
                "reason": "newer valid Unicode source selected" if item["path"] != selected.get("path") else "current source",
            }
            for item in stale
        ],
        "requires_user_comparison_approval": status == "ambiguous_needs_comparison_approval",
    }
    write_json(STATE_ROOT / "CANONICAL_LYRIC_SOURCE.json", canonical)
    return canonical


def normalize_canonical_lyrics(canonical: dict[str, Any]) -> list[dict[str, Any]]:
    selected = canonical.get("selected", {})
    path = Path(selected.get("path", ""))
    text = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
    phrases = []
    repeated: dict[str, int] = {}
    for line_number, raw in enumerate(text.splitlines(), start=1):
        exact = raw.rstrip("\n")
        stripped = exact.strip()
        if not stripped:
            continue
        category = line_category(stripped)
        normalized = normalize_unicode(stripped)
        base = slug_line(normalized)
        repeated[base] = repeated.get(base, 0) + 1
        occurrence_id = f"{base}_occurrence_{repeated[base]}"
        phrases.append(
            {
                "line_number": line_number,
                "occurrence_index": repeated[base],
                "occurrence_id": occurrence_id,
                "category": category,
                "exact_source_text": exact,
                "normalized_unicode": normalized,
                "punctuation": "".join(ch for ch in stripped if not ch.isalnum() and not BURMESE_RE.match(ch) and not ch.isspace()),
                "pronunciation": normalized,
                "candidate_correction": "",
                "user_approved_correction": "",
            }
        )
    payload = {
        "source": selected,
        "phrases": phrases,
        "lyric_occurrence_count": sum(1 for p in phrases if p["category"] == "lyric"),
        "title_credit_section_count": sum(1 for p in phrases if p["category"] != "lyric"),
    }
    write_json(AUDIO_TRUTH_ROOT / "NORMALIZED_LYRICS.json", payload)
    return phrases


def audio_model_bundle_status() -> dict[str, Any]:
    approval_path = AUDIO_TRUTH_ROOT / "LOCAL_BURMESE_AUDIO_INTELLIGENCE_BUNDLE.json"
    existing = read_json(approval_path, {})
    approved = existing.get("approval_status") == "approved"
    tools = {
        "demucs": executable_status(REPO_ROOT / "local-tools" / "envs" / "facefusion" / "bin" / "demucs"),
        "mlx_whisper": executable_status(REPO_ROOT / "local-tools" / "envs" / "facefusion" / "bin" / "mlx_whisper"),
        "ffmpeg": executable_status(Path(discover_binary("ffmpeg") or "/opt/homebrew/bin/ffmpeg")),
        "ffprobe": executable_status(Path(discover_binary("ffprobe") or "/opt/homebrew/bin/ffprobe")),
    }
    bundle = {
        "approval_title": "LOCAL BURMESE AUDIO INTELLIGENCE BUNDLE",
        "approval_status": "approved" if approved else "pending",
        "reason": "Needed before Demucs separation, Burmese ASR ensemble, and CTC forced alignment can be trusted.",
        "detected_tools": tools,
        "options": [
            {
                "id": "balanced",
                "name": "Recommended balanced bundle",
                "models": [
                    {
                        "name": "YonaKhine/finetuned-w2v2-bert-burmese-asr",
                        "purpose": "Primary Burmese CTC evidence and known-text forced alignment",
                        "source": "https://huggingface.co/YonaKhine/finetuned-w2v2-bert-burmese-asr",
                        "license": "MIT per model card",
                        "size_note": "0.6B params per model card; exact file download size to be confirmed before install",
                    },
                    {
                        "name": "myatsu/whisper-small-burmese-v4",
                        "purpose": "Lightweight Burmese Whisper second opinion",
                        "source": "https://huggingface.co/myatsu/whisper-small-burmese-v4",
                        "license": "check model card before install",
                        "size_note": "0.2B params per model card",
                    },
                    {
                        "name": "Demucs",
                        "purpose": "Local vocal separation",
                        "source": "https://github.com/facebookresearch/demucs",
                        "license": "MIT per upstream repository",
                        "size_note": "runtime installed; pretrained weights require approval/download if not cached",
                    },
                ],
            },
            {
                "id": "lightweight",
                "name": "Lightweight bundle",
                "models": ["myatsu/whisper-small-burmese-v4", "Demucs vocals stem"],
            },
            {
                "id": "heavier",
                "name": "Higher-accuracy/heavier bundle",
                "models": ["YonaKhine CTC", "Chonlasitk/whisper-burmese", "Demucs htdemucs"],
            },
        ],
        "no_cloud_upload": True,
        "no_paid_api": True,
        "install_allowed": approved,
    }
    write_json(approval_path, bundle)
    return bundle


def prepare_vocal_separation(bundle: dict[str, Any]) -> dict[str, Any]:
    stems_dir = AUDIO_TRUTH_ROOT / "stems"
    stems_dir.mkdir(parents=True, exist_ok=True)
    full_mix = stems_dir / "full_mix_normalized_16k.wav"
    log = stems_dir / "separation_metadata.log"
    if not full_mix.exists():
        run_ffmpeg(["-y", "-i", str(MASTER_AUDIO), "-ac", "1", "-ar", "16000", str(full_mix)], log)
    master_meta = probe_media(MASTER_AUDIO)
    full_meta = probe_media(full_mix) if full_mix.exists() else {}
    status = "blocked_pending_model_approval"
    reason = "Demucs model execution/download requires LOCAL BURMESE AUDIO INTELLIGENCE BUNDLE approval."
    vocals = stems_dir / "vocals.wav"
    instrumental = stems_dir / "instrumental.wav"
    if bundle.get("install_allowed") and vocals.exists() and instrumental.exists():
        status = "separated_existing_stems"
        reason = "Existing stems found and approved."
    metadata = {
        "status": status,
        "reason": reason,
        "master_audio": str(MASTER_AUDIO),
        "master_metadata": master_meta,
        "full_mix_normalized_16k": str(full_mix),
        "full_mix_metadata": full_meta,
        "vocals_wav": str(vocals) if vocals.exists() else "",
        "instrumental_wav": str(instrumental) if instrumental.exists() else "",
        "duration_matches_master": abs(float(master_meta.get("duration") or 0) - float(full_meta.get("duration") or 0)) <= 0.5 if full_meta else False,
        "hashes": {
            "master": sha256_file(MASTER_AUDIO) if MASTER_AUDIO.exists() else "",
            "full_mix_normalized_16k": sha256_file(full_mix) if full_mix.exists() else "",
            "vocals": sha256_file(vocals) if vocals.exists() else "",
        },
        "tool": "Demucs",
        "tool_revision": "not_run_in_v2_2_without_bundle_approval",
    }
    write_json(stems_dir / "separation_metadata.json", metadata)
    return metadata


def run_asr_ensemble_status(bundle: dict[str, Any], stems: dict[str, Any]) -> dict[str, Any]:
    asr_root = AUDIO_TRUTH_ROOT / "asr"
    asr_root.mkdir(parents=True, exist_ok=True)
    models = [
        "YonaKhine/finetuned-w2v2-bert-burmese-asr",
        "Chonlasitk/whisper-burmese",
        "myatsu/whisper-small-burmese-v4",
    ]
    records = []
    for model in models:
        model_dir = asr_root / safe_name(model)
        model_dir.mkdir(parents=True, exist_ok=True)
        record = {
            "model": model,
            "status": "blocked_pending_bundle_approval",
            "audio_source": stems.get("vocals_wav") or stems.get("full_mix_normalized_16k"),
            "raw_segments": [],
            "transcript": "",
            "confidence": {},
            "run_metadata": {"no_cloud_upload": True, "no_paid_api": True},
        }
        write_json(model_dir / "raw_segments.json", [])
        (model_dir / "transcript.txt").write_text("", encoding="utf-8")
        write_json(model_dir / "timestamps.json", [])
        write_json(model_dir / "confidence.json", {})
        write_json(model_dir / "run_metadata.json", record)
        records.append(record)
    payload = {
        "status": "blocked_pending_bundle_approval",
        "models": records,
        "agreement": "not_available_until_models_run",
        "warning": "No ASR output is treated as truth until local approved models are benchmarked.",
    }
    write_json(asr_root / "ASR_ENSEMBLE_STATUS.json", payload)
    return payload


def build_audio_truth_timeline(canonical: dict[str, Any], phrases: list[dict[str, Any]], bundle: dict[str, Any], stems: dict[str, Any], asr: dict[str, Any]) -> dict[str, Any]:
    brain = read_json(STATE_ROOT / "PRODUCTION_BRAIN_TIMELINE.json", {})
    prior_events = [event for event in brain.get("events", []) if event.get("approved_unicode")]
    lyric_phrases = [p for p in phrases if p["category"] == "lyric"]
    occurrences = []
    for idx, phrase in enumerate(lyric_phrases):
        prior = prior_events[idx] if idx < len(prior_events) else {}
        status = "needs_audio_model_approval"
        confidence = 0.0
        if bundle.get("approval_status") == "approved" and asr.get("status") != "blocked_pending_bundle_approval":
            status = "needs_targeted_review"
            confidence = 0.35
        occurrences.append(
            {
                "phrase_id": idx + 1,
                "occurrence_id": phrase["occurrence_id"],
                "canonical_unicode_lyric": phrase["normalized_unicode"],
                "source_line": phrase["line_number"],
                "candidate_corrected_lyric": "",
                "phrase_start": prior.get("caption_start") or prior.get("start"),
                "phrase_end": prior.get("caption_end") or prior.get("end"),
                "word_timing": [],
                "syllable_timing": [],
                "vocal_onset": prior.get("start"),
                "vocal_offset": prior.get("end"),
                "asr_transcripts": [],
                "ctc_alignment_score": 0.0,
                "model_agreement": "not_available",
                "phrase_order_score": 0.5 if prior else 0.0,
                "repeated_line_mapping": repeated_mapping(phrase, lyric_phrases),
                "confidence": confidence,
                "evidence": ["canonical_unicode_source", "previous_brain_timing_not_audio_truth"],
                "status": status,
                "blockers": ["LOCAL_BURMESE_AUDIO_INTELLIGENCE_BUNDLE_APPROVAL_REQUIRED"],
            }
        )
    timeline = {
        "version": "audio-truth-v1",
        "master_song": str(MASTER_AUDIO),
        "master_duration": probe_media(MASTER_AUDIO).get("duration") if MASTER_AUDIO.exists() else 0,
        "canonical_lyric_source": canonical,
        "alignment_basis": "blocked_until_ctc_asr_bundle_approved",
        "occurrences": occurrences,
        "instrumental_regions": brain.get("song_sections", []),
        "production_caption_allowed": False,
        "lipsync_allowed": False,
    }
    write_json(STATE_ROOT / "AUDIO_TRUTH_TIMELINE.json", timeline)
    return timeline


def verify_lyrics(canonical: dict[str, Any], phrases: list[dict[str, Any]], timeline: dict[str, Any]) -> dict[str, Any]:
    unresolved = []
    for occ in timeline["occurrences"]:
        unresolved.append(
            {
                "occurrence_id": occ["occurrence_id"],
                "line": occ["canonical_unicode_lyric"],
                "status": "needs_model_evidence",
                "reason": "No ASR/CTC evidence has been approved and run yet.",
            }
        )
    payload = {
        "canonical_source": canonical,
        "status": "blocked_pending_audio_model_bundle",
        "missing_line_count": 0,
        "extra_line_count": 0,
        "possible_spelling_error_count": 0,
        "repeated_chorus_missing_count": 0,
        "unresolved": unresolved[:8],
        "unresolved_count": len(unresolved),
        "auto_accepted_normalization_count": 0,
    }
    write_json(STATE_ROOT / "LYRIC_TEXT_VERIFICATION.json", payload)
    return payload


def build_meaning_performance_map(timeline: dict[str, Any]) -> dict[str, Any]:
    phrases = []
    for occ in timeline["occurrences"]:
        text = occ["canonical_unicode_lyric"]
        phrases.append(
            {
                "occurrence_id": occ["occurrence_id"],
                "canonical_burmese": text,
                "literal_english_meaning": rough_meaning(text),
                "natural_english_meaning": rough_meaning(text),
                "pronunciation_helper": text,
                "narrative_meaning": "heartbreak memory and emotional pressure",
                "emotional_intention": emotional_intent(text),
                "vocal_energy": "unmeasured_until_vocal_stem",
                "loudness": "pending",
                "pitch_movement": "pending",
                "music_energy": "from existing MUSIC_ANALYSIS until audio truth models run",
                "section": "unknown_until_alignment",
                "performance_direction": "restrained adult pain, no karaoke acting",
                "facial_expression_direction": "small controlled expression, profile-safe when possible",
                "body_movement_direction": "grounded movement below shoulder height",
                "camera_purpose": "support lyric meaning only after occurrence timing is trusted",
                "lighting_purpose": "amber/crimson pressure against cold window",
                "lip_sync_importance": "blocked_until_occurrence_aligned",
                "evidence": ["lyric_semantics", "director_inference", "uncertain"],
            }
        )
    payload = {"version": "audio-truth-v1", "phrases": phrases}
    write_json(STATE_ROOT / "SONG_MEANING_PERFORMANCE_MAP.json", payload)
    return payload


def rebuild_audio_truth_captions(timeline: dict[str, Any], verification: dict[str, Any]) -> dict[str, Any]:
    CAPTION_ROOT.mkdir(parents=True, exist_ok=True)
    review_items = [
        {
            "index": 1,
            "start": 0.0,
            "end": min(6.0, float(timeline.get("master_duration") or 6.0)),
            "text": "AUDIO TRUTH PENDING - Burmese lyric timing blocked until local ASR/CTC bundle is approved.",
        }
    ]
    write_srt(CAPTION_ROOT / "CAPTIONS_AUDIO_TRUTH_REVIEW.srt", review_items)
    write_vtt(CAPTION_ROOT / "CAPTIONS_AUDIO_TRUTH_REVIEW.vtt", review_items)
    write_ass(CAPTION_ROOT / "CAPTIONS_AUDIO_TRUTH_REVIEW.ass", review_items)
    blockers = {
        "production_captions_ready": False,
        "blockers": [
            "LOCAL_BURMESE_AUDIO_INTELLIGENCE_BUNDLE_APPROVAL_REQUIRED",
            "NO_CTC_FORCED_ALIGNMENT_RUN",
            "NO_ASR_ENSEMBLE_EVIDENCE",
            "LYRIC_TEXT_VERIFICATION_BLOCKED",
        ],
    }
    write_json(CAPTION_ROOT / "ALIGNMENT_STATUS.json", timeline)
    write_json(CAPTION_ROOT / "LYRIC_VERIFICATION.json", verification)
    write_json(CAPTION_ROOT / "CAPTION_BLOCKERS.json", blockers)
    return {
        "path": str(CAPTION_ROOT),
        "review_srt": str(CAPTION_ROOT / "CAPTIONS_AUDIO_TRUTH_REVIEW.srt"),
        "production_ready": False,
        "blocked_phrase_count": len(timeline["occurrences"]),
        "blockers": blockers["blockers"],
    }


def build_lipsync_segments(timeline: dict[str, Any]) -> dict[str, Any]:
    root = AUDIO_TRUTH_ROOT / "lipsync-segments"
    root.mkdir(parents=True, exist_ok=True)
    ready = 0
    blocked = []
    for occ in timeline["occurrences"]:
        occ_dir = root / occ["occurrence_id"]
        occ_dir.mkdir(parents=True, exist_ok=True)
        (occ_dir / f"{occ['occurrence_id']}_lyric.txt").write_text(occ["canonical_unicode_lyric"], encoding="utf-8")
        (occ_dir / f"{occ['occurrence_id']}_pronunciation.txt").write_text(occ["canonical_unicode_lyric"], encoding="utf-8")
        write_json(occ_dir / f"{occ['occurrence_id']}_timing.json", {"status": "blocked", "blockers": occ["blockers"]})
        write_json(occ_dir / f"{occ['occurrence_id']}_meaning.json", {"status": "pending_alignment"})
        blocked.append({"occurrence_id": occ["occurrence_id"], "blockers": occ["blockers"]})
    payload = {
        "ready_occurrence_count": ready,
        "blocked_occurrence_count": len(blocked),
        "blocked": blocked,
        "status": "blocked_pending_audio_truth_alignment",
    }
    write_json(root / "LIPSYNC_SEGMENT_STATUS.json", payload)
    return payload


def build_audio_truth_video_sketch(captions: dict[str, Any], timeline: dict[str, Any]) -> dict[str, Any]:
    PREVIEW_ROOT.mkdir(parents=True, exist_ok=True)
    source = ENGINE_ROOT / "animatics" / "15" / "ANIMATIC.mp4"
    clean = PREVIEW_ROOT / "CREATIVE_SKETCH_AUDIO_TRUTH.mp4"
    captioned = PREVIEW_ROOT / "CREATIVE_SKETCH_AUDIO_TRUTH_WITH_CAPTIONS.mp4"
    review = PREVIEW_ROOT / "CREATIVE_SKETCH_AUDIO_TRUTH_REVIEW.mp4"
    if source.exists():
        shutil.copy2(source, clean)
        shutil.copy2(source, captioned)
        shutil.copy2(source, review)
    metadata = probe_media(clean) if clean.exists() else {}
    validation = {
        "master_duration": probe_media(MASTER_AUDIO).get("duration") if MASTER_AUDIO.exists() else 0,
        "preview_duration": metadata.get("duration", 0),
        "difference": abs(float(metadata.get("duration") or 0) - float(probe_media(MASTER_AUDIO).get("duration") if MASTER_AUDIO.exists() else 0)),
        "status": "ok" if metadata else "missing",
        "caption_status": "audio_truth_pending_no_lyric_captions_burned",
    }
    write_json(PREVIEW_ROOT / "DURATION_VALIDATION.json", validation)
    write_json(PREVIEW_ROOT / "AUDIO_TRUTH_EVALUATION.json", {"status": "blocked_pending_model_approval", "metadata": metadata, "timeline_status": timeline["alignment_basis"]})
    write_json(PREVIEW_ROOT / "BUILD_LOG.txt", {"source": str(source), "note": "Copied clean full-song sketch; lyric captions blocked until audio truth alignment."})
    write_timeline_png(PREVIEW_ROOT / "CAPTION_TIMING_PLOT.png", timeline, caption_regions=False)
    write_timeline_png(PREVIEW_ROOT / "VOCAL_AND_CAPTION_TIMELINE.png", timeline, caption_regions=False)
    return {
        "path": str(PREVIEW_ROOT),
        "clean": str(clean),
        "captioned": str(captioned),
        "review": str(review),
        "metadata": metadata,
        "duration_validation": validation,
        "label": "LOCAL AUDIO-TRUTH REVIEW SKETCH - LYRICS BLOCKED UNTIL ALIGNMENT",
    }


def update_production_brain_audio_truth(timeline: dict[str, Any], meaning: dict[str, Any], captions: dict[str, Any], lipsync: dict[str, Any]) -> dict[str, Any]:
    brain = read_json(STATE_ROOT / "PRODUCTION_BRAIN.json", {})
    brain["audio_truth"] = {
        "timeline_path": str(STATE_ROOT / "AUDIO_TRUTH_TIMELINE.json"),
        "canonical_lyric_source_path": str(STATE_ROOT / "CANONICAL_LYRIC_SOURCE.json"),
        "meaning_map_path": str(STATE_ROOT / "SONG_MEANING_PERFORMANCE_MAP.json"),
        "captions": captions,
        "lipsync": lipsync,
        "status": "blocked_pending_local_audio_model_bundle",
    }
    brain["lyrics"] = timeline["occurrences"]
    brain["captions"] = {"source": "AUDIO_TRUTH_TIMELINE.json", "production_ready": False}
    brain["lip_sync"] = {"source": "AUDIO_TRUTH_TIMELINE.json", "ready_occurrence_count": lipsync["ready_occurrence_count"]}
    brain["meaning"] = meaning
    write_json(STATE_ROOT / "PRODUCTION_BRAIN.json", brain)
    return {"path": str(STATE_ROOT / "PRODUCTION_BRAIN.json"), "status": brain["audio_truth"]["status"]}


def studio_audio_truth_context() -> dict[str, Any]:
    status = audio_truth_status()
    if status.get("version") == "v2.4.1":
        canonical_path = status.get("canonical_lyric_source", "")
        anchor_state = read_json(STATE_ROOT / "AUDIO_TRUTH_ANCHORS_V4.json", {})
        status = dict(status)
        status["anchor_records"] = anchor_state.get("anchors", [])
        status["display_mode"] = "audio_truth_repair"
        return {
            "audio_truth": status,
            "canonical": {
                "selected": {"filename": Path(canonical_path).name, "path": canonical_path},
                "encoding": "unicode",
                "status": "selected_manual_unicode_audio_truth_v4",
                "previous_sources": [
                    {
                        "status": "superseded_stale_retained_for_history",
                        "path": str(PROJECT_ROOT / "inputs" / "51b07bfca4c4-Zawgyi.txt"),
                    }
                ],
            },
            "bundle": {
                "approval_status": "approved_installed",
                "reason": "Balanced local Burmese Audio Intelligence Bundle installed; V4 anchor/playback repair run.",
                "options": [],
            },
            "timeline": read_json(STATE_ROOT / "AUDIO_TRUTH_TIMELINE_V4.json", {}),
            "preview_url": "/studio-assets/burmese-music-video/previews/audio-truth-v4/CREATIVE_SKETCH_AUDIO_TRUTH_V4_WITH_CAPTIONS.mp4",
        }
    if status.get("version") == "v2.4":
        canonical_path = status.get("canonical_lyric_source", "")
        anchor_state = read_json(STATE_ROOT / "AUDIO_TRUTH_ANCHORS.json", {})
        status = dict(status)
        status["anchor_records"] = anchor_state.get("anchors", [])
        return {
            "audio_truth": status,
            "canonical": {
                "selected": {"filename": Path(canonical_path).name, "path": canonical_path},
                "encoding": "unicode",
                "status": "selected_manual_unicode_audio_truth_v3",
                "previous_sources": [
                    {
                        "status": "superseded_stale_retained_for_history",
                        "path": str(PROJECT_ROOT / "inputs" / "51b07bfca4c4-Zawgyi.txt"),
                    }
                ],
            },
            "bundle": {
                "approval_status": "approved_installed",
                "reason": "Balanced local Burmese Audio Intelligence Bundle installed; V3 constrained calibration run.",
                "options": [],
            },
            "timeline": read_json(STATE_ROOT / "AUDIO_TRUTH_TIMELINE_V3.json", {}),
            "preview_url": "/studio-assets/burmese-music-video/previews/audio-truth-v3/CREATIVE_SKETCH_AUDIO_TRUTH_V3_WITH_CAPTIONS.mp4",
        }
    if status.get("version") == "v2.3":
        canonical_path = status.get("canonical_lyric_source", "")
        return {
            "audio_truth": status,
            "canonical": {
                "selected": {"filename": Path(canonical_path).name, "path": canonical_path},
                "encoding": "unicode",
                "status": "selected_manual_unicode_audio_truth_v2",
                "previous_sources": [
                    status.get("canonical_source_audit", {}).get("stale_zawgyi_copy", {})
                ],
            },
            "bundle": {
                "approval_status": "approved_installed",
                "reason": "Balanced local Burmese Audio Intelligence Bundle installed and run locally.",
                "options": [],
            },
            "timeline": read_json(STATE_ROOT / "AUDIO_TRUTH_TIMELINE_V2.json", {}),
            "preview_url": "/studio-assets/burmese-music-video/previews/audio-truth-v2/CREATIVE_SKETCH_AUDIO_TRUTH_V2.mp4",
        }
    return {
        "audio_truth": status,
        "canonical": status.get("canonical_lyric_source", {}),
        "bundle": status.get("model_bundle", {}),
        "timeline": read_json(STATE_ROOT / "AUDIO_TRUTH_TIMELINE.json", {}),
        "preview_url": "/studio-assets/burmese-music-video/previews/audio-truth-v1/CREATIVE_SKETCH_AUDIO_TRUTH.mp4",
    }


def line_category(line: str) -> str:
    lowered = line.strip().lower()
    if not lowered:
        return "blank"
    if lowered.startswith(("v", "cho", "chorus", "verse", "bridge")) and len(lowered) <= 12:
        return "section"
    if "တေးရေး" in line or "ေတးေရး" in line or "composer" in lowered:
        return "credit"
    if len(line) < 30 and ("ဇာတ်လမ်း" in line or "ဇာတ္လမ္း" in line):
        return "title"
    return "lyric" if BURMESE_RE.search(line) else "section"


def detect_encoding(text: str) -> tuple[str, float]:
    zawgyi_markers = ["ေ", "္", "ဲ႕", "ေ၀", "ကၽ", "ႏ", "ဳ", "ဴ"]
    unicode_markers = ["ျ", "ြ", "ှ", "့", "ဦ", "က္", "င်္"]
    zawgyi_score = sum(text.count(marker) for marker in zawgyi_markers)
    unicode_score = sum(text.count(marker) for marker in unicode_markers)
    if zawgyi_score > unicode_score + 2:
        return "zawgyi", min(0.95, 0.55 + zawgyi_score / 40)
    if unicode_score >= zawgyi_score:
        return "unicode", min(0.98, 0.65 + unicode_score / 40)
    return "mixed_or_uncertain", 0.5


def normalize_unicode(text: str) -> str:
    return " ".join(text.strip().split())


def similarity_to_brain(lines: list[str]) -> float:
    brain = read_json(STATE_ROOT / "PRODUCTION_BRAIN_TIMELINE.json", {})
    brain_text = "\n".join(str(event.get("approved_unicode") or event.get("caption_text") or "") for event in brain.get("events", []))
    if not lines or not brain_text:
        return 0.0
    joined = "\n".join(lines)
    shared = len(set(joined.split()) & set(brain_text.split()))
    total = max(1, len(set(joined.split()) | set(brain_text.split())))
    return round(shared / total, 3)


def appears_manually_edited(path: Path, text: str) -> bool:
    return path.parent.name == "lyrics" and "Zawgyi" not in path.name and detect_encoding(text)[0] == "unicode"


def executable_status(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"found": False, "path": str(path), "version": ""}
    try:
        result = subprocess.run([str(path), "--help"], capture_output=True, text=True, timeout=8, check=False)
        return {"found": True, "path": str(path), "health": "help_ok" if result.returncode == 0 else "help_error", "version": (result.stdout or result.stderr).splitlines()[0] if (result.stdout or result.stderr) else ""}
    except Exception as exc:
        return {"found": True, "path": str(path), "health": f"error:{type(exc).__name__}", "version": str(exc)}


def repeated_mapping(phrase: dict[str, Any], phrases: list[dict[str, Any]]) -> dict[str, Any]:
    same = [p for p in phrases if p["normalized_unicode"] == phrase["normalized_unicode"]]
    return {"repeated": len(same) > 1, "occurrence_index": phrase["occurrence_index"], "total_occurrences": len(same)}


def rough_meaning(text: str) -> str:
    if "အနမ်း" in text:
        return "a kiss has turned into longing and an ending"
    if "အမုန်း" in text:
        return "hatred, loss and a forced smile after love"
    if "အလင်း" in text or "အမှောင်" in text:
        return "darkness, silence and inner burden"
    if "မတွေ့" in text or "ဝေး" in text:
        return "searching, distance and separation"
    return "heartbreak memory; exact translation needs human review"


def emotional_intent(text: str) -> str:
    if "ဝေး" in text or "လွမ်း" in text:
        return "longing and distance"
    if "ဒဏ်ရာ" in text or "ကွဲ" in text:
        return "wound and pressure"
    if "အမှောင်" in text:
        return "quiet darkness"
    return "restrained heartbreak"


def write_srt(path: Path, items: list[dict[str, Any]]) -> None:
    lines = []
    for item in items:
        lines.extend([str(item["index"]), f"{srt_time(item['start'])} --> {srt_time(item['end'])}", item["text"], ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_vtt(path: Path, items: list[dict[str, Any]]) -> None:
    lines = ["WEBVTT", ""]
    for item in items:
        lines.extend([f"{vtt_time(item['start'])} --> {vtt_time(item['end'])}", item["text"], ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_ass(path: Path, items: list[dict[str, Any]]) -> None:
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Myanmar MN,58,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,3,1,2,100,100,80,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = [f"Dialogue: 0,{ass_time(item['start'])},{ass_time(item['end'])},Default,,0,0,0,,{item['text']}" for item in items]
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")


def srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def vtt_time(seconds: float) -> str:
    return srt_time(seconds).replace(",", ".")


def ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02}:{s:05.2f}"


def write_timeline_png(path: Path, timeline: dict[str, Any], caption_regions: bool) -> None:
    width, height = 1200, 220
    pixels = bytearray()
    duration = float(timeline.get("master_duration") or 1)
    regions = timeline.get("occurrences", [])
    for y in range(height):
        row = bytearray()
        for x in range(width):
            base = (16, 17, 18)
            t = x / width * duration
            active = any((occ.get("phrase_start") or -1) <= t <= (occ.get("phrase_end") or -2) for occ in regions if occ.get("phrase_start") is not None)
            if 92 <= y <= 126 and active:
                base = (214, 155, 73) if caption_regions else (120, 90, 60)
            if y in {90, 127}:
                base = (52, 48, 44)
            row.extend(base)
        pixels.extend(b"\x00" + row)
    raw = bytes(pixels)
    def chunk(kind: bytes, data: bytes) -> bytes:
        return len(data).to_bytes(4, "big") + kind + data + zlib.crc32(kind + data).to_bytes(4, "big")
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", width.to_bytes(4, "big") + height.to_bytes(4, "big") + b"\x08\x02\x00\x00\x00") + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
    path.write_bytes(png)


def _next_action(bundle: dict[str, Any], timeline: dict[str, Any], verification: dict[str, Any]) -> str:
    if bundle.get("approval_status") != "approved":
        return "Approve the single LOCAL BURMESE AUDIO INTELLIGENCE BUNDLE or continue without production captions/lip-sync."
    if verification.get("unresolved_count"):
        return "Review only the unresolved lyric lines after ASR/CTC alignment."
    return "Review audio-truth captions and promote aligned occurrences."


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")


def slug_line(value: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:8]
    return f"lyric_line_{digest}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _iso_from_mtime(mtime: float) -> str:
    import datetime

    return datetime.datetime.fromtimestamp(mtime).isoformat()


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
