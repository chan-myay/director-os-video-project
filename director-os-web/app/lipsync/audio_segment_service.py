from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import ENGINE_ROOT, REPO_ROOT
from app.system_tools.ffmpeg_service import run_ffmpeg


def prepare_audio_segment(run_id: int, shot_id: str, start: float, end: float) -> dict[str, Any]:
    root = ENGINE_ROOT / "lipsync" / str(run_id) / shot_id
    root.mkdir(parents=True, exist_ok=True)
    master = REPO_ROOT / "audio" / "01.mp3"
    vocal = root / "VOCAL_SEGMENT.wav"
    full_mix = root / "FULL_MIX_SEGMENT.wav"
    log_path = root / "AUDIO_BUILD_LOG.txt"
    duration = max(end - start, 0.25)
    args = ["-y", "-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-i", str(master), "-ar", "44100", "-ac", "1", str(full_mix)]
    result = run_ffmpeg(args, log_path)
    if full_mix.exists():
        vocal.write_bytes(full_mix.read_bytes())
    lyrics = root / "LYRICS.txt"
    pronunciation = root / "PRONUNCIATION_HELPER.txt"
    lyrics.write_text("UNKNOWN lyric line; link to Burmese lyric timeline before production lip-sync.\n", encoding="utf-8")
    pronunciation.write_text("UNKNOWN pronunciation helper; audio remains authoritative.\n", encoding="utf-8")
    metadata = {
        "source_audio": str(master),
        "start_time": start,
        "end_time": end,
        "duration": duration,
        "sample_rate": 44100,
        "channels": 1,
        "ffmpeg_returncode": result.returncode,
        "full_mix_segment": str(full_mix),
        "vocal_segment": str(vocal),
    }
    (root / "AUDIO_SEGMENT_METADATA.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata
