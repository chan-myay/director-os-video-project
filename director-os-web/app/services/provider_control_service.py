from __future__ import annotations

from typing import Any

from app.intelligence.provider_health import provider_status
from app.services.v09_studio_service import run_status


def provider_capacity_status() -> dict[str, Any]:
    status = provider_status()
    return {
        "active_provider": status.get("active_provider", status.get("provider", "")),
        "health": status,
        "capacity": "unknown_until_request",
        "known_warning": "CODEX_PROVIDER_USAGE_LIMIT is preserved on runs that hit quota.",
    }


def resume_provider_run(run_id: int) -> dict[str, Any]:
    status = run_status(run_id)
    blockers = status.get("blockers", [])
    fallback_stages = [blocker.split(":", 1)[1] for blocker in blockers if blocker.startswith("PROVIDER_FALLBACK_USED:")]
    usage_limited = "CODEX_PROVIDER_USAGE_LIMIT" in blockers
    return {
        "run_id": run_id,
        "status": "awaiting_provider_capacity" if usage_limited else "ready_for_provider_resume",
        "fallback_marked_stages": fallback_stages,
        "will_modify_outputs": False,
        "message": (
            "Provider capacity is currently exhausted or was exhausted on this run; no retries were launched."
            if usage_limited
            else "Fallback-marked stages can be retried with the real provider when explicitly launched from the run page."
        ),
    }
