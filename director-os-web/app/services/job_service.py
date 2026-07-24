from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from app.config import ENGINE_ROOT, JOB_PACKAGE_ROOT, REPO_ROOT
from app.services.asset_policy_service import (
    evaluate_asset_policy,
    latest_approved_gate,
    reference_lines,
    required_references_for_shot,
)
from app.services.audit_service import write_audit
from app.services.connector_dryrun_service import run_connector_dry_run
from app.services.db import connect, initialize_database
from app.services.engine_reader import read_text
from app.services.workflow_service import get_shot_pack_record


JOB_STATUSES = {
    "draft",
    "waiting_approval",
    "approved",
    "dry_run_ready",
    "dry_run_complete",
    "blocked",
    "submitted",
    "running",
    "completed",
    "failed",
    "rejected_by_qc",
}


def _request_record(shot_pack_id: int, filename: str) -> Optional[dict[str, Any]]:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM generated_requests WHERE shot_pack_id = ? AND filename = ?",
            (shot_pack_id, filename),
        ).fetchone()
    return dict(row) if row else None


def generated_request_options(shot_id: str) -> list[dict[str, Any]]:
    shot = get_shot_pack_record(shot_id)
    if not shot:
        return []
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM generated_requests WHERE shot_pack_id = ? ORDER BY filename",
            (shot["id"],),
        ).fetchall()
    return [dict(row) for row in rows]


def list_jobs() -> list[dict[str, Any]]:
    initialize_database()
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT generation_jobs.*, shot_packs.shot_id
            FROM generation_jobs
            JOIN shot_packs ON shot_packs.id = generation_jobs.shot_pack_id
            ORDER BY generation_jobs.id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_job(shot_id: str, job_id: int) -> Optional[dict[str, Any]]:
    initialize_database()
    with connect() as conn:
        row = conn.execute(
            """
            SELECT generation_jobs.*, shot_packs.shot_id
            FROM generation_jobs
            JOIN shot_packs ON shot_packs.id = generation_jobs.shot_pack_id
            WHERE generation_jobs.id = ? AND shot_packs.shot_id = ?
            """,
            (job_id, shot_id),
        ).fetchone()
        if not row:
            return None
        job = dict(row)
        job["assets"] = [dict(asset) for asset in conn.execute("SELECT * FROM job_assets WHERE job_id = ? ORDER BY id", (job_id,)).fetchall()]
        job["events"] = [dict(event) for event in conn.execute("SELECT * FROM job_events WHERE job_id = ? ORDER BY id DESC", (job_id,)).fetchall()]
        job["outputs"] = [dict(output) for output in conn.execute("SELECT * FROM job_outputs WHERE job_id = ? ORDER BY id DESC", (job_id,)).fetchall()]
    return job


def _path_from_relative(relative_path: str) -> Path:
    return REPO_ROOT / relative_path


def _reference_role(shot_id: str, reference_path: str) -> str:
    for role, required_path in required_references_for_shot(shot_id).items():
        if required_path in reference_path:
            return role
    return "reference"


def _write_package_files(
    package_dir: Path,
    job_id: int,
    shot_id: str,
    renderer: str,
    request: dict[str, Any],
    references: list[str],
    spend_upload_limit: str,
    privacy_acknowledged: bool,
    policy: dict[str, Any],
) -> None:
    package_dir.mkdir(parents=True, exist_ok=True)
    request_text = read_text(_path_from_relative(request["path"]))
    negative_text = read_text(ENGINE_ROOT / "generated-requests" / shot_id / "08_NEGATIVE_LOCK.md")
    qc_text = read_text(ENGINE_ROOT / "generated-requests" / shot_id / "09_QC_SCORECARD.md")

    manifest = [
        f"job_id: {job_id}",
        f"shot_id: {shot_id}",
        f"renderer: {renderer}",
        f"request_filename: {request['filename']}",
        f"status: {'blocked' if policy['blocked'] else 'dry_run_ready'}",
        f"reference_complete: {str(policy['reference_completeness']['complete']).lower()}",
        f"real_generation_readiness: {str(policy['real_generation_readiness']).lower()}",
        "real_connector_execution: false",
        "media_copied: false",
        "api_called: false",
        "upload_performed: false",
        f"blocked_reasons: {json.dumps(policy['blockers'])}",
        f"warnings: {json.dumps(policy['warnings'])}",
    ]
    (package_dir / "JOB_MANIFEST.yaml").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    (package_dir / "FINAL_REQUEST.md").write_text(request_text, encoding="utf-8")
    reference_lines_out = ["# Approved References", ""]
    required = required_references_for_shot(shot_id)
    present_roles = policy["reference_completeness"]["present"]
    for role, required_path in required.items():
        status = "present" if role in present_roles else "missing"
        reference_lines_out.append(f"- {role}: {required_path} [{status}]")
    extra_refs = [ref for ref in references if not any(required_path in ref for required_path in required.values())]
    if extra_refs:
        reference_lines_out.extend(["", "## Extra References"])
        reference_lines_out.extend(f"- extra: {ref}" for ref in extra_refs)
    (package_dir / "APPROVED_REFERENCES.md").write_text("\n".join(reference_lines_out) + "\n", encoding="utf-8")
    (package_dir / "PRIVACY_GATE.md").write_text(
        "# Privacy Gate\n\n"
        f"- Privacy acknowledged: {privacy_acknowledged}\n"
        "- No child-containing sources allowed.\n"
        "- No rejected reference sheets allowed.\n"
        "- No broad private lead performer/source folders allowed.\n"
        "- v0.5 performs no upload.\n",
        encoding="utf-8",
    )
    (package_dir / "SPEND_GATE.md").write_text(
        "# Spend Gate\n\n"
        f"- Spend/upload limit: {spend_upload_limit or 'MISSING'}\n"
        "- v0.5 performs no paid API call.\n",
        encoding="utf-8",
    )
    (package_dir / "NEGATIVE_LOCK.md").write_text(negative_text, encoding="utf-8")
    (package_dir / "QC_TARGET.md").write_text(qc_text, encoding="utf-8")
    (package_dir / "CONNECTOR_DRY_RUN.md").write_text(
        "# Connector Dry Run\n\nDry-run has not been executed yet.\n",
        encoding="utf-8",
    )
    (package_dir / "READINESS_REPORT.md").write_text(
        _readiness_markdown(job_id, shot_id, renderer, policy),
        encoding="utf-8",
    )
    (package_dir / "AUDIT_SNAPSHOT.md").write_text(
        "# Audit Snapshot\n\n"
        f"- Job ID: {job_id}\n"
        f"- Shot ID: {shot_id}\n"
        f"- Renderer: {renderer}\n"
        f"- Blocked: {policy['blocked']}\n"
        f"- Blockers: {', '.join(policy['blockers']) if policy['blockers'] else 'none'}\n"
        f"- Reference complete: {policy['reference_completeness']['complete']}\n"
        f"- Real generation readiness: {policy['real_generation_readiness']}\n"
        "- No media copied.\n"
        "- No API called.\n"
        "- No upload performed.\n",
        encoding="utf-8",
    )


def _readiness_markdown(job_id: int, shot_id: str, renderer: str, policy: dict[str, Any]) -> str:
    completeness = policy["reference_completeness"]
    lines = [
        f"# Real-Generation Readiness - Job {job_id}",
        "",
        "No API call was made. No media was uploaded. No video was generated.",
        "",
        f"- Shot ID: {shot_id}",
        f"- Renderer: {renderer}",
        f"- Reference complete: {completeness['complete']}",
        f"- Real generation readiness: {policy['real_generation_readiness']}",
        "",
        "## Required References",
        "",
    ]
    lines.extend(f"- {role}: {path}" for role, path in completeness["required"].items())
    lines.extend(["", "## Present References", ""])
    if not completeness["present"]:
        lines.append("- none")
    else:
        lines.extend(f"- {role}: {path}" for role, path in completeness["present"].items())
    lines.extend(["", "## Missing References", ""])
    if not completeness["missing"]:
        lines.append("- none")
    else:
        lines.extend(f"- {role}: {path}" for role, path in completeness["missing"].items())
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {blocker}" for blocker in policy["blockers"] or [])
    if not policy["blockers"]:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def create_job(shot_id: str, form: dict[str, str]) -> tuple[bool, str, Optional[int]]:
    initialize_database()
    shot = get_shot_pack_record(shot_id)
    if not shot:
        return False, "Unknown shot pack.", None

    renderer = form.get("renderer", "").strip()
    request_filename = form.get("request_filename", "").strip()
    spend_upload_limit = form.get("spend_upload_limit", "").strip()
    privacy_acknowledged = form.get("privacy_acknowledged") == "on"

    if not renderer or not request_filename:
        return False, "Renderer and generated request file are required.", None

    request = _request_record(shot["id"], request_filename)
    if not request:
        return False, "Unknown generated request file.", None

    approval = latest_approved_gate(shot["id"], renderer)
    references_text = approval["exact_references"] if approval else form.get("exact_references", "")
    policy = evaluate_asset_policy(shot["id"], shot_id, renderer, spend_upload_limit, privacy_acknowledged, references_text)
    status = "blocked" if policy["blocked"] else "dry_run_ready"

    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO generation_jobs
                (shot_pack_id, renderer, request_filename, spend_upload_limit,
                 privacy_acknowledged, status, blocked_reasons)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                shot["id"],
                renderer,
                request_filename,
                spend_upload_limit,
                1 if privacy_acknowledged else 0,
                status,
                json.dumps(policy["blockers"], sort_keys=True),
            ),
        )
        job_id = int(cursor.lastrowid)
        package_dir = JOB_PACKAGE_ROOT / shot_id / str(job_id)
        conn.execute(
            "UPDATE generation_jobs SET package_path = ? WHERE id = ?",
            (str(package_dir), job_id),
        )
        for ref in reference_lines(references_text):
            conn.execute(
                """
                INSERT INTO job_assets (job_id, path, role, policy_status, notes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    ref,
                    _reference_role(shot_id, ref),
                    "blocked" if policy["blocked"] else "approved_for_dry_run",
                    "path reference only; media not copied",
                ),
            )
        conn.execute(
            """
            INSERT INTO job_events (job_id, event_type, summary, metadata)
            VALUES (?, 'job_created', ?, ?)
            """,
            (job_id, f"Job package created with status {status}", json.dumps({"blockers": policy["blockers"]}, sort_keys=True)),
        )

    _write_package_files(
        package_dir,
        job_id,
        shot_id,
        renderer,
        request,
        policy["references"],
        spend_upload_limit,
        privacy_acknowledged,
        policy,
    )

    write_audit(
        "generation_job_created",
        "generation_jobs",
        str(job_id),
        f"Frozen job package created for {shot_id} with status {status}",
        {"shot_id": shot_id, "renderer": renderer, "status": status, "blockers": policy["blockers"]},
    )
    return True, f"Job package created with status {status}.", job_id


def run_job_dry_run(shot_id: str, job_id: int) -> tuple[bool, str]:
    job = get_job(shot_id, job_id)
    if not job:
        return False, "Unknown job."
    package_dir = Path(job["package_path"])
    ok, message = run_connector_dry_run(job_id, package_dir)
    if ok:
        write_audit(
            "generation_job_dry_run",
            "generation_jobs",
            str(job_id),
            f"Dry-run validation completed for {shot_id}",
            {"shot_id": shot_id, "job_id": job_id},
        )
    return ok, message


def job_readiness(shot_id: str, job_id: int) -> Optional[dict[str, Any]]:
    job = get_job(shot_id, job_id)
    if not job:
        return None
    readiness_path = Path(job["package_path"]) / "READINESS_REPORT.md"
    return {
        "job": job,
        "path": str(readiness_path),
        "content": read_text(readiness_path),
    }
