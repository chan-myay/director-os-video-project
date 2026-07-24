from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class LipSyncProviderHealth:
    provider: str
    classification: str
    status: str
    health: dict[str, Any]


class LipSyncProvider:
    name = "base"
    classification = "unavailable"

    def health(self) -> LipSyncProviderHealth:
        return LipSyncProviderHealth(self.name, self.classification, "not_configured", {})

    def package_only(self, job: dict[str, Any]) -> dict[str, Any]:
        return {"status": "manual_package_only", "provider": self.name, "job": job}
