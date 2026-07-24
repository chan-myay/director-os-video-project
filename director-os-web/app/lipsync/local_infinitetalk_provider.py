from __future__ import annotations

from pathlib import Path

from app.config import REPO_ROOT
from app.lipsync.base_provider import LipSyncProviderHealth
from app.lipsync.infinitetalk_provider import InfiniteTalkProvider


class LocalInfiniteTalkProvider(InfiniteTalkProvider):
    name = "local_infinitetalk"
    classification = "local_after_install"

    def health(self) -> LipSyncProviderHealth:
        candidates = [
            REPO_ROOT / "local-tools/research-repos/InfiniteTalk",
            REPO_ROOT / "local-tools/InfiniteTalk",
        ]
        found = [str(path) for path in candidates if path.exists()]
        return LipSyncProviderHealth(
            provider=self.name,
            classification=self.classification,
            status="code_found_not_operational" if found else "not_installed",
            health={
                "found_paths": found,
                "model_downloaded": False,
                "operational": False,
                "reason": "No approved local InfiniteTalk model benchmark exists.",
            },
        )
