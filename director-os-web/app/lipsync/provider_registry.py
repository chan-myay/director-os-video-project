from __future__ import annotations

import json
from typing import Any

from app.lipsync.local_infinitetalk_provider import LocalInfiniteTalkProvider
from app.lipsync.manual_infinitetalk_provider import ManualInfiniteTalkProvider
from app.lipsync.runpod_infinitetalk_provider import RunPodInfiniteTalkProvider
from app.services.db import connect, initialize_database


def providers() -> list[Any]:
    return [LocalInfiniteTalkProvider(), RunPodInfiniteTalkProvider(), ManualInfiniteTalkProvider()]


def refresh_lipsync_provider_health() -> list[dict[str, Any]]:
    initialize_database()
    rows = []
    with connect() as conn:
        for provider in providers():
            health = provider.health()
            row = {
                "provider": health.provider,
                "classification": health.classification,
                "status": health.status,
                "health": health.health,
            }
            rows.append(row)
            conn.execute(
                """
                INSERT INTO lipsync_provider_health (provider, classification, status, health, last_checked)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(provider) DO UPDATE SET
                    classification = excluded.classification,
                    status = excluded.status,
                    health = excluded.health,
                    last_checked = CURRENT_TIMESTAMP
                """,
                (health.provider, health.classification, health.status, json.dumps(health.health, ensure_ascii=False)),
            )
    return rows
