from __future__ import annotations

from app.lipsync.base_provider import LipSyncProvider, LipSyncProviderHealth


class InfiniteTalkProvider(LipSyncProvider):
    name = "infinitetalk"
    classification = "private_remote_option"

    def health(self) -> LipSyncProviderHealth:
        return LipSyncProviderHealth(
            provider=self.name,
            classification=self.classification,
            status="researched_not_installed",
            health={
                "modes": ["video_to_video_dubbing", "image_to_video_talking_singing"],
                "local_install": "requires explicit approval; not installed by Director OS",
                "runpod": "optional user-controlled endpoint; disabled until approved",
            },
        )
