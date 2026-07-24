from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.system_tools.binary_discovery import binary_version, discover_binary


def system_tool_health() -> dict[str, Any]:
    ffmpeg = discover_binary("ffmpeg")
    ffprobe = discover_binary("ffprobe")
    return {
        "ffmpeg": {
            "found": bool(ffmpeg),
            "path": ffmpeg or "",
            "version": binary_version(ffmpeg),
        },
        "ffprobe": {
            "found": bool(ffprobe),
            "path": ffprobe or "",
            "version": binary_version(ffprobe),
        },
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "failure_reason": "" if ffmpeg and ffprobe else "FFmpeg/FFprobe not found or not executable",
    }
