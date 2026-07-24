from __future__ import annotations

import shutil
from typing import Any


def local_asr_status() -> dict[str, Any]:
    candidates = [
        ("mlx_whisper", shutil.which("mlx_whisper")),
        ("whisper", shutil.which("whisper")),
    ]
    found = [{"name": name, "path": path} for name, path in candidates if path]
    return {
        "available": bool(found),
        "providers": found,
        "used_for_current_sync": False,
        "reason": "No local ASR provider is used unless already installed and explicitly suitable for this audio.",
    }
