from __future__ import annotations

from typing import Any

from app.services.audit_service import write_audit
from app.services.db import connect, initialize_database
from app.services.workflow_service import get_shot_pack_record


VALID_APPROVAL_DECISIONS = {"approve", "reject"}


def list_approvals(shot_id: str) -> list[dict[str, Any]]:
    initialize_database()
    shot = get_shot_pack_record(shot_id)
    if not shot:
        return []
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM approval_gates WHERE shot_pack_id = ? ORDER BY id DESC",
            (shot["id"],),
        ).fetchall()
    return [dict(row) for row in rows]


def create_approval(shot_id: str, form: dict[str, str]) -> tuple[bool, str]:
    initialize_database()
    shot = get_shot_pack_record(shot_id)
    if not shot:
        return False, "Unknown shot pack."

    renderer = form.get("renderer_selected", "").strip()
    references = form.get("exact_references", "").strip()
    spend_limit = form.get("spend_upload_limit", "").strip()
    decision = form.get("decision", "").strip()
    notes = form.get("notes", "").strip()
    privacy_ack = form.get("privacy_warning_acknowledged") == "on"
    final_reviewed = form.get("final_request_reviewed") == "on"

    if decision not in VALID_APPROVAL_DECISIONS:
        return False, "Decision must be approve or reject."
    if not renderer or not references or not spend_limit:
        return False, "Renderer, exact references, and spend/upload limit are required."
    if not privacy_ack or not final_reviewed:
        return False, "Privacy warning and final request review must be acknowledged."

    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO approval_gates
                (shot_pack_id, renderer_selected, exact_references,
                 privacy_warning_acknowledged, spend_upload_limit,
                 final_request_reviewed, decision, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (shot["id"], renderer, references, 1, spend_limit, 1, decision, notes),
        )
        approval_id = cursor.lastrowid

    write_audit(
        "approval_gate_recorded",
        "approval_gates",
        str(approval_id),
        f"{decision} recorded for {shot_id} using {renderer}",
        {"shot_id": shot_id, "renderer": renderer, "decision": decision},
    )
    return True, "Approval gate recorded."
