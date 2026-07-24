from __future__ import annotations

import json
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path
from typing import Any, Optional

from app.config import REPO_ROOT


LOCAL_BIN_DIR = REPO_ROOT / "local-tools" / "envs" / "faceswap" / "bin"


def find_binary(name: str) -> Optional[str]:
    candidates = [
        shutil.which(name),
        str(LOCAL_BIN_DIR / name),
        f"/opt/homebrew/bin/{name}",
        f"/usr/local/bin/{name}",
        f"/usr/bin/{name}",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def _parse_fps(value: str) -> float:
    if not value or value == "0/0":
        return 0.0
    try:
        return float(Fraction(value))
    except (ValueError, ZeroDivisionError):
        return 0.0


def probe_video(path: Path) -> dict[str, Any]:
    ffprobe = find_binary("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe not found")
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    data = json.loads(result.stdout)
    video_stream = next((stream for stream in data.get("streams", []) if stream.get("codec_type") == "video"), {})
    return {
        "duration": float(data.get("format", {}).get("duration") or video_stream.get("duration") or 0),
        "width": int(video_stream.get("width") or 0),
        "height": int(video_stream.get("height") or 0),
        "fps": _parse_fps(video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate") or ""),
        "codec": video_stream.get("codec_name", ""),
    }


def extract_poster(video_path: Path, poster_path: Path) -> None:
    ffmpeg = find_binary("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found")
    subprocess.run(
        [ffmpeg, "-y", "-i", str(video_path), "-vf", "thumbnail,scale=640:-1", "-frames:v", "1", str(poster_path)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def extract_contact_sheet(video_path: Path, contact_sheet_path: Path) -> None:
    ffmpeg = find_binary("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found")
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(video_path),
            "-vf",
            "fps=1,scale=240:-1,tile=3x2",
            "-frames:v",
            "1",
            str(contact_sheet_path),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
