from __future__ import annotations

from app.lipsync.base_provider import LipSyncProviderHealth
from app.lipsync.infinitetalk_provider import InfiniteTalkProvider


class ManualInfiniteTalkProvider(InfiniteTalkProvider):
    name = "manual_infinitetalk"
    classification = "private_remote_option"

    def health(self) -> LipSyncProviderHealth:
        return LipSyncProviderHealth(
            provider=self.name,
            classification=self.classification,
            status="available_manual_package_only",
            health={"upload": "manual_only_after_user_approval", "api_calls": False, "paid_execution": False},
        )
