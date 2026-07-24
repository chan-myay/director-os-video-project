from __future__ import annotations

import os

from app.lipsync.base_provider import LipSyncProviderHealth
from app.lipsync.infinitetalk_provider import InfiniteTalkProvider


class RunPodInfiniteTalkProvider(InfiniteTalkProvider):
    name = "runpod_infinitetalk"
    classification = "private_remote_option"

    def health(self) -> LipSyncProviderHealth:
        configured = bool(os.environ.get("RUNPOD_API_KEY")) and (
            bool(os.environ.get("RUNPOD_INFINITETALK_ENDPOINT_ID")) or bool(os.environ.get("RUNPOD_INFINITETALK_BASE_URL"))
        )
        return LipSyncProviderHealth(
            provider=self.name,
            classification=self.classification,
            status="configured_disabled_until_approval" if configured else "not_configured",
            health={
                "api_key_present": bool(os.environ.get("RUNPOD_API_KEY")),
                "endpoint_id_present": bool(os.environ.get("RUNPOD_INFINITETALK_ENDPOINT_ID")),
                "base_url_present": bool(os.environ.get("RUNPOD_INFINITETALK_BASE_URL")),
                "max_cost_usd": os.environ.get("RUNPOD_MAX_COST_USD", ""),
                "max_runtime_minutes": os.environ.get("RUNPOD_MAX_RUNTIME_MINUTES", ""),
                "submission_enabled": False,
            },
        )
