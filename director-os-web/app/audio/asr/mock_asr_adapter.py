from __future__ import annotations

from pathlib import Path

from app.audio.asr.base import ASRResult


class MockASRAdapter:
    name = "mock_asr"

    def health(self) -> dict[str, object]:
        return {"provider": self.name, "available": True, "path": "test-only", "downloads_performed": False}

    def transcribe(self, audio_path: Path) -> ASRResult:
        return ASRResult(self.name, True, "mock transcript", [{"start": 0, "end": 1, "text": "mock"}], ["test_only"])
