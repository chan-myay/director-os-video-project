from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ProviderResponse:
    provider_name: str
    provider_version: str
    raw_text: str
    data: dict[str, Any]
    stdout: str
    stderr: str
    exit_status: int
    timed_out: bool
    started_at: float
    ended_at: float


class IntelligenceProvider(ABC):
    name = "base"
    version = "unknown"

    @abstractmethod
    def health(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def complete_stage(self, stage: str, context: dict[str, Any], timeout: int = 120) -> ProviderResponse:
        raise NotImplementedError
