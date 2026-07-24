from __future__ import annotations

import os
from typing import Any

from app.intelligence.codex_provider import CodexProvider
from app.intelligence.fallback_provider import FallbackProvider
from app.intelligence.mock_provider import MockProvider
from app.intelligence.provider import IntelligenceProvider


def active_provider() -> IntelligenceProvider:
    mode = os.environ.get("DIRECTOR_OS_INTELLIGENCE_PROVIDER", "codex").lower()
    if mode == "mock":
        return MockProvider()
    if mode == "fallback":
        return FallbackProvider()
    provider = CodexProvider()
    if provider.health()["available"]:
        return provider
    return FallbackProvider()


def provider_status() -> dict[str, Any]:
    provider = active_provider()
    health = provider.health()
    health["fallback_status"] = "active" if provider.name != "codex_cli" else "available_not_active"
    health["credentials_exposed"] = False
    return health
