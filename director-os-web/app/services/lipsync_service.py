from __future__ import annotations

from typing import Any

from app.lipsync.lipsync_planner import (
    build_lipsync_plan,
    create_lipsync_job,
    create_manual_infinitetalk_export,
    get_lipsync_job,
    list_lipsync_jobs,
)
from app.lipsync.provider_registry import refresh_lipsync_provider_health
from app.lipsync.shot_eligibility_service import classify_lipsync_shots
from app.services.db import connect, initialize_database


def lipsync_dashboard() -> dict[str, Any]:
    initialize_database()
    jobs = list_lipsync_jobs()
    providers = refresh_lipsync_provider_health()
    eligibility = classify_lipsync_shots()
    return {"jobs": jobs, "providers": providers, "eligibility": eligibility}


def lipsync_outputs_for_job(job_id: int) -> list[dict[str, Any]]:
    initialize_database()
    with connect() as conn:
        rows = conn.execute("SELECT * FROM lipsync_outputs WHERE job_id = ? ORDER BY output_id DESC", (job_id,)).fetchall()
    return [dict(row) for row in rows]


def lipsync_output(output_id: int) -> dict[str, Any] | None:
    initialize_database()
    with connect() as conn:
        row = conn.execute("SELECT * FROM lipsync_outputs WHERE output_id = ?", (output_id,)).fetchone()
    return dict(row) if row else None


__all__ = [
    "build_lipsync_plan",
    "classify_lipsync_shots",
    "create_lipsync_job",
    "create_manual_infinitetalk_export",
    "get_lipsync_job",
    "lipsync_dashboard",
    "lipsync_output",
    "lipsync_outputs_for_job",
    "list_lipsync_jobs",
    "refresh_lipsync_provider_health",
]
