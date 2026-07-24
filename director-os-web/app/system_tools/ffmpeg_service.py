from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from app.system_tools.binary_discovery import discover_binary


def ffmpeg_path() -> str:
    path = discover_binary("ffmpeg")
    if not path:
        raise RuntimeError("FFmpeg not found. Set DIRECTOR_OS_FFMPEG or install ffmpeg.")
    return path


def ffprobe_path() -> str:
    path = discover_binary("ffprobe")
    if not path:
        raise RuntimeError("FFprobe not found. Set DIRECTOR_OS_FFPROBE or install ffmpeg.")
    return path


def probe_media(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        [ffprobe_path(), "-v", "error", "-show_format", "-show_streams", "-print_format", "json", str(path)],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    data = json.loads(result.stdout)
    video = next((stream for stream in data.get("streams", []) if stream.get("codec_type") == "video"), {})
    audio = next((stream for stream in data.get("streams", []) if stream.get("codec_type") == "audio"), {})
    return {
        "duration": float(data.get("format", {}).get("duration") or 0),
        "size": int(data.get("format", {}).get("size") or path.stat().st_size),
        "format": data.get("format", {}).get("format_name", ""),
        "video_codec": video.get("codec_name", ""),
        "audio_codec": audio.get("codec_name", ""),
        "width": int(video.get("width") or 0),
        "height": int(video.get("height") or 0),
        "streams": len(data.get("streams", [])),
    }


def run_ffmpeg(args: list[str], log_path: Path) -> subprocess.CompletedProcess[str]:
    command = [ffmpeg_path(), *args]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    with log_path.open("a", encoding="utf-8") as log:
        log.write("$ " + " ".join(command) + "\n")
        log.write(result.stdout)
        log.write(result.stderr)
        log.write("\n")
    return result
