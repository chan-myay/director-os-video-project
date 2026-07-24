from __future__ import annotations

import shutil
from pathlib import Path

from app.audio.asr.base import ASRResult


class WhisperCppAdapter:
    name = "whisper_cpp"

    def health(self) -> dict[str, object]:
        path = shutil.which("whisper-cli") or shutil.which("main")
        return {"provider": self.name, "available": bool(path), "path": path or "", "downloads_performed": False}

    def transcribe(self, audio_path: Path) -> ASRResult:
        return ASRResult(self.name, False, "", [], ["not_run_without_existing_model_and_burmese_validation"])
