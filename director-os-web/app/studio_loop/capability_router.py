from __future__ import annotations

from typing import Any


def capability_matrix() -> dict[str, Any]:
    return {
        "llm_reasoning": {"provider": "codex_or_mock", "classification": "local_or_provider", "approval_required": False},
        "music_analysis": {"provider": "ffmpeg_ffprobe_waveform", "classification": "local", "approval_required": False},
        "captioning": {"provider": "local_subtitle_export", "classification": "local", "approval_required": False},
        "editing_composition": {"provider": "ffmpeg", "classification": "local", "approval_required": False},
        "qc": {"provider": "local_probe_and_rules", "classification": "local", "approval_required": False},
        "image_generation": {"provider": "none_operational", "classification": "local_after_install", "approval_required": True},
        "video_generation": {"provider": "none_operational", "classification": "cloud_optional_or_local_after_install", "approval_required": True},
        "asr": {"provider": "none_detected", "classification": "local_after_install", "approval_required": True},
        "voice": {"provider": "none_configured", "classification": "local_after_install_or_cloud_optional", "approval_required": True},
        "lip_sync": {"provider": "infinitetalk_not_installed", "classification": "private_remote_option_or_local_after_install", "approval_required": True},
    }


def route_for_task(task: str) -> dict[str, Any]:
    matrix = capability_matrix()
    if task in {"song_music", "caption_sync", "editing", "assembly", "qc", "repair"}:
        return matrix["music_analysis" if task == "song_music" else "editing_composition" if task in {"editing", "assembly"} else "qc" if task in {"qc", "repair"} else "captioning"]
    return matrix.get(task, {"provider": "local_rules", "classification": "local", "approval_required": False})
