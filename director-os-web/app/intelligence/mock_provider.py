from __future__ import annotations

import time
from typing import Any

from app.intelligence.provider import IntelligenceProvider, ProviderResponse


class MockProvider(IntelligenceProvider):
    name = "mock_provider"
    version = "test"

    def health(self) -> dict[str, Any]:
        return {"provider": self.name, "available": True, "runtime": "test-only", "version": self.version}

    def complete_stage(self, stage: str, context: dict[str, Any], timeout: int = 120) -> ProviderResponse:
        started = time.time()
        data: dict[str, Any] = {
            "stage": stage,
            "summary": f"Mock output for {stage}",
            "confidence": 0.7,
            "sources": [{"source": "mock test context", "confidence": 0.7}],
            "artifacts": [f"{stage}.json"],
            "blockers": [],
            "data": {"stage": stage, "mock": True, "idea": context.get("idea", "")},
        }
        ended = time.time()
        return ProviderResponse(self.name, self.version, str(data), data, "", "", 0, False, started, ended)
