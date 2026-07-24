from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from app.audio.asr.base import ASRResult


class MLXWhisperAdapter:
    name = "mlx_whisper"

    def health(self) -> dict[str, Any]:
        path = shutil.which("mlx_whisper")
        return {"provider": self.name, "available": bool(path), "path": path or "", "downloads_performed": False}

    def transcribe(self, audio_path: Path) -> ASRResult:
        return ASRResult(self.name, False, "", [], ["not_run_without_existing_model_and_burmese_validation"])
