from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import ENGINE_ROOT
from app.audio.brain_sync_service import brain_lipsync_readiness, brain_timeline_status
from app.services.lyric_timing_service import voice_sync_summary
from app.services.v104_animatic_sync_service import caption_readiness, font_check


ANIMATIC_ROOT = ENGINE_ROOT / "animatics"
ALLOWED_ASSET_EXTENSIONS = {".mp4", ".json", ".txt", ".srt", ".vtt", ".ass", ".png", ".wav"}


def latest_safe_animatic_context() -> dict[str, Any]:
    ANIMATIC_ROOT.mkdir(parents=True, exist_ok=True)
    versions = [_version_context(path) for path in sorted(ANIMATIC_ROOT.iterdir(), key=_version_sort) if path.is_dir()]
    non_defective = [
        version
        for version in versions
        if version["exists"]
        and not version["defective"]
        and version["validation"].get("status") in {"ok", "warning"}
        and version["clean_mp4_exists"]
    ]
    active = non_defective[-1] if non_defective else (versions[-1] if versions else _empty_context())
    cap_ready = caption_readiness()
    voice = voice_sync_summary()
    lipsync = brain_lipsync_readiness()
    brain = brain_timeline_status()
    active.update(
        {
            "available_versions": versions,
            "brain": brain,
            "caption_readiness": cap_ready,
            "voice_sync": voice,
            "voice_sync_status": voice.get("status", "not_tested_no_voice_audio"),
            "lipsync": lipsync,
            "warnings": _warnings(active, versions, cap_ready, voice, lipsync),
            "next_action": "Review the Run 14 brain-sync animatic, then approve or correct the proposed global caption offset.",
        }
    )
    return active


def resolve_director_asset(asset_path: str) -> tuple[Path | None, int, str]:
    root = ENGINE_ROOT.resolve()
    if "\x00" in asset_path:
        return None, 400, "invalid asset path"
    path = (root / asset_path).resolve()
    if not str(path).startswith(str(root)):
        return None, 403, "path traversal blocked"
    if path.suffix.lower() not in ALLOWED_ASSET_EXTENSIONS:
        return None, 403, "asset type is not allowed"
    if not path.exists() or not path.is_file():
        return None, 404, "asset not found"
    return path, 200, "ok"


def diagnose_animatic_route() -> dict[str, Any]:
    context = latest_safe_animatic_context()
    return {
        "route": "/animatic",
        "status": "ok",
        "active_version": context.get("latest_version"),
        "clean_mp4_exists": context.get("clean_mp4_exists"),
        "captioned_review_exists": context.get("captioned_review_exists"),
        "review_mp4_exists": context.get("review_mp4_exists"),
        "warnings": context.get("warnings", []),
        "latest_safe_url": f"http://127.0.0.1:8787/animatic",
    }


def _version_context(path: Path) -> dict[str, Any]:
    status = _read_json(path / "SUPERSEDED_STATUS.json")
    validation = _read_json(path / "DURATION_VALIDATION.json")
    font = _read_json(path / "FONT_STATUS.json") or _read_json(path / "CAPTION_FONT_STATUS.json") or font_check()
    sync = (
        _read_json(path / "BRAIN_SYNC_STATUS.json")
        or _read_json(path / "AUTO_SYNC_STATUS.json")
        or _read_json(path / "CAPTION_SYNC_STATUS.json")
    )
    clean = path / "ANIMATIC.mp4"
    calibrated_captioned = path / "ANIMATIC_WITH_CAPTIONS_SYNC_CALIBRATED_REVIEW.mp4"
    brain_captioned = path / "ANIMATIC_WITH_CAPTIONS_BRAIN_SYNC_REVIEW.mp4"
    captioned = path / "ANIMATIC_WITH_CAPTIONS_REVIEW.mp4"
    legacy_captioned = path / "ANIMATIC_WITH_CAPTIONS.mp4"
    review = path / "ANIMATIC_REVIEW.mp4"
    defective = status.get("status") == "superseded_review_defective" or validation.get("status") == "hard_failure"
    return {
        "latest_version": path.name,
        "latest_path": str(path),
        "exists": path.exists(),
        "defective": defective,
        "superseded_status": status,
        "validation": validation,
        "font": font,
        "sync": sync or {"status": "missing_sync_status"},
        "clean_mp4": str(clean),
        "captioned_review_mp4": str(calibrated_captioned if calibrated_captioned.exists() else (brain_captioned if brain_captioned.exists() else (captioned if captioned.exists() else legacy_captioned))),
        "review_mp4": str(review),
        "clean_mp4_exists": clean.exists(),
        "captioned_review_exists": calibrated_captioned.exists() or brain_captioned.exists() or captioned.exists() or legacy_captioned.exists(),
        "review_mp4_exists": review.exists(),
        "clean_asset_url": f"/director-assets/animatics/{path.name}/ANIMATIC.mp4",
        "captioned_review_asset_url": f"/director-assets/animatics/{path.name}/{'ANIMATIC_WITH_CAPTIONS_SYNC_CALIBRATED_REVIEW.mp4' if calibrated_captioned.exists() else ('ANIMATIC_WITH_CAPTIONS_BRAIN_SYNC_REVIEW.mp4' if brain_captioned.exists() else ('ANIMATIC_WITH_CAPTIONS_REVIEW.mp4' if captioned.exists() else 'ANIMATIC_WITH_CAPTIONS.mp4'))}",
        "review_asset_url": f"/director-assets/animatics/{path.name}/ANIMATIC_REVIEW.mp4",
    }


def _empty_context() -> dict[str, Any]:
    return {
        "latest_version": "none",
        "latest_path": "",
        "exists": False,
        "defective": False,
        "validation": {},
        "font": font_check(),
        "sync": {"status": "no_safe_animatic_yet"},
        "clean_mp4_exists": False,
        "captioned_review_exists": False,
        "review_mp4_exists": False,
        "clean_asset_url": "",
        "captioned_review_asset_url": "",
        "review_asset_url": "",
    }


def _warnings(active: dict[str, Any], versions: list[dict[str, Any]], cap_ready: dict[str, Any], voice: dict[str, Any], lipsync: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if not active.get("clean_mp4_exists"):
        warnings.append("LATEST_CLEAN_ANIMATIC_MISSING")
    if active.get("defective"):
        warnings.append("ACTIVE_ANIMATIC_DEFECTIVE")
    if not active.get("captioned_review_exists"):
        warnings.append("CAPTIONED_REVIEW_MP4_MISSING")
    if not active.get("font", {}).get("readable"):
        warnings.append("READABLE_BURMESE_FONT_MISSING")
    if not cap_ready.get("production_captions_ready"):
        warnings.append("PRODUCTION_CAPTIONS_BLOCKED")
    if voice.get("status") == "not_tested_no_voice_audio":
        warnings.append("VOICE_SYNC_NOT_TESTED")
    if lipsync.get("readiness_status") != "ready":
        warnings.append(lipsync.get("readiness_status", "LIPSYNC_NOT_READY"))
    if any(version.get("superseded_status", {}).get("status") == "superseded_review_defective" for version in versions):
        warnings.append("DEFECTIVE_RUN11_PRESERVED_AND_SUPERSEDED")
    return warnings


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _version_sort(path: Path) -> int:
    return int(path.name) if path.name.isdigit() else -1
