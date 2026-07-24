from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config import REPO_ROOT
from app.services.asset_policy_service import reference_completeness
from app.services.db import connect, initialize_database


def _read_request_markdown(relative_path: str) -> str:
    path = REPO_ROOT / relative_path
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def build_dry_run_markdown(job: dict[str, Any], request: dict[str, Any], assets: list[dict[str, Any]]) -> str:
    request_text = _read_request_markdown(request["path"])
    missing = []
    if not request_text.strip():
        missing.append("request markdown could not be read")
    if not job["renderer"]:
        missing.append("renderer is missing")
    if not job["spend_upload_limit"]:
        missing.append("spend/upload limit is missing")
    if not assets:
        missing.append("approved reference list is empty")

    would_upload = [asset["path"] for asset in assets]
    completeness = reference_completeness(job["shot_id"], would_upload)
    real_generation_readiness = bool(
        request_text.strip()
        and job["renderer"]
        and job["spend_upload_limit"]
        and assets
        and completeness["complete"]
        and job["status"] != "blocked"
    )
    privacy_risks = []
    if would_upload:
        privacy_risks.append("private/person reference paths would require explicit upload approval in a real connector")
    if job["renderer"] not in {"comfyui", "wan"}:
        privacy_risks.append("selected renderer is not marked local-only")

    lines = [
        f"# Connector Dry Run - Job {job['id']}",
        "",
        "No API call was made. No media was uploaded. No video was generated.",
        "",
        "## Request Validation",
        "",
        f"- Shot pack: {job['shot_id']}",
        f"- Renderer: {job['renderer']}",
        f"- Request file: {job['request_filename']}",
        f"- Status before dry-run: {job['status']}",
        f"- Spend/upload limit: {job['spend_upload_limit']}",
        f"- Reference complete: {completeness['complete']}",
        f"- Real generation readiness: {real_generation_readiness}",
        "",
        "## Missing Fields",
        "",
    ]
    lines.extend([f"- {item}" for item in missing] or ["- none"])
    lines.extend(["", "## Required References", ""])
    lines.extend([f"- {role}: {path}" for role, path in completeness["required"].items()] or ["- none"])
    lines.extend(["", "## Present References", ""])
    lines.extend([f"- {role}: {path}" for role, path in completeness["present"].items()] or ["- none"])
    lines.extend(["", "## Missing References", ""])
    lines.extend([f"- {role}: {path}" for role, path in completeness["missing"].items()] or ["- none"])
    lines.extend(["", "## Would-Upload Files", ""])
    lines.extend([f"- {item}" for item in would_upload] or ["- none"])
    lines.extend(["", "## Privacy Risks", ""])
    lines.extend([f"- {item}" for item in privacy_risks] or ["- none"])
    lines.extend(
        [
            "",
            "## Cost Risk",
            "",
            "- UNKNOWN. v0.5 does not call paid APIs or estimate live pricing.",
            "",
            "## Dry-Run Result",
            "",
            "- Connector remains disabled/stub.",
            "- Real submitted/running/completed states are not used in v0.5.",
        ]
    )
    return "\n".join(lines) + "\n"


def run_connector_dry_run(job_id: int, package_dir: Path) -> tuple[bool, str]:
    initialize_database()
    with connect() as conn:
        job_row = conn.execute(
            """
            SELECT generation_jobs.*, shot_packs.shot_id
            FROM generation_jobs
            JOIN shot_packs ON shot_packs.id = generation_jobs.shot_pack_id
            WHERE generation_jobs.id = ?
            """,
            (job_id,),
        ).fetchone()
        if not job_row:
            return False, "Unknown job."
        job = dict(job_row)
        request_row = conn.execute(
            """
            SELECT * FROM generated_requests
            WHERE shot_pack_id = ? AND filename = ?
            """,
            (job["shot_pack_id"], job["request_filename"]),
        ).fetchone()
        if not request_row:
            return False, "Unknown request file."
        assets = [dict(row) for row in conn.execute("SELECT * FROM job_assets WHERE job_id = ? ORDER BY id", (job_id,)).fetchall()]

    package_dir.mkdir(parents=True, exist_ok=True)
    dry_run_path = package_dir / "CONNECTOR_DRY_RUN.md"
    content = build_dry_run_markdown(job, dict(request_row), assets)
    dry_run_path.write_text(content, encoding="utf-8")

    final_status = "dry_run_complete" if job["status"] != "blocked" else "blocked"
    with connect() as conn:
        conn.execute(
            """
            UPDATE generation_jobs
            SET status = ?, dry_run_summary = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (final_status, "dry-run written; no API/upload/generation", job_id),
        )
        conn.execute(
            """
            INSERT INTO job_events (job_id, event_type, summary, metadata)
            VALUES (?, 'dry_run_completed', 'Connector dry-run package written', '{}')
            """,
            (job_id,),
        )
        conn.execute(
            """
            INSERT INTO job_outputs (job_id, output_type, path, status, notes)
            VALUES (?, 'dry_run_report', ?, 'dry_run', 'No media output; markdown validation report only')
            """,
            (job_id, str(dry_run_path)),
        )

    return True, "Dry-run report written."
