from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ASRResult:
    provider: str
    available: bool
    raw_transcript: str
    segments: list[dict[str, Any]]
    warnings: list[str]


class ASRProvider(ABC):
    name: str

    @abstractmethod
    def health(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def transcribe(self, audio_path: Path) -> ASRResult:
        raise NotImplementedError
