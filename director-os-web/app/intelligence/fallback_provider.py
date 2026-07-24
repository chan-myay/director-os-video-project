from __future__ import annotations

import time
from typing import Any

from app.intelligence.provider import IntelligenceProvider, ProviderResponse


class FallbackProvider(IntelligenceProvider):
    name = "fallback_structured"
    version = "0.9"

    def health(self) -> dict[str, Any]:
        return {"provider": self.name, "available": True, "runtime": "local deterministic fallback", "version": self.version}

    def complete_stage(self, stage: str, context: dict[str, Any], timeout: int = 120) -> ProviderResponse:
        started = time.time()
        data: dict[str, Any] = {
            "stage": stage,
            "summary": f"Fallback structured output for {stage}. Codex provider was unavailable or skipped.",
            "confidence": 0.42,
            "sources": [{"source": "local fallback provider", "confidence": 0.4}],
            "artifacts": [],
            "blockers": ["REAL_INTELLIGENCE_PROVIDER_NOT_USED"],
            "data": {"stage": stage, "fallback": True, "idea": context.get("idea", "")},
        }
        ended = time.time()
        return ProviderResponse(self.name, self.version, str(data), data, "", "", 0, False, started, ended)
