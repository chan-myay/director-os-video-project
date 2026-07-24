from __future__ import annotations

from typing import Any, Optional

from app.services.audit_service import write_audit
from app.services.db import connect, initialize_database


def list_motion_references(shot_id: str | None = None) -> list[dict[str, Any]]:
    initialize_database()
    query = "SELECT * FROM motion_references"
    params: tuple[Any, ...] = ()
    if shot_id:
        query += " WHERE shot_id = ?"
        params = (shot_id,)
    query += " ORDER BY motion_id DESC"
    with connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def get_latest_motion_reference(shot_id: str) -> Optional[dict[str, Any]]:
    initialize_database()
    with connect() as conn:
        row = conn.execute(
            """
            SELECT * FROM motion_references
            WHERE shot_id = ?
            ORDER BY motion_id DESC
            LIMIT 1
            """,
            (shot_id,),
        ).fetchone()
    return dict(row) if row else None


def create_motion_reference(form: dict[str, str]) -> tuple[bool, str, Optional[int]]:
    initialize_database()
    shot_id = form.get("shot_id", "F01_side_travel_dance").strip() or "F01_side_travel_dance"
    source = form.get("source", "").strip()
    source_title = form.get("source_title", "").strip()
    if not source or not source_title:
        return False, "Source path/URL and source title are required.", None
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO motion_references
                (shot_id, source_type, source, source_title, owner_license,
                 permitted_use, start_time, end_time, body_framing,
                 travel_direction, speed, face_visibility, rights_status,
                 source_owner_license, transfer_body_movement, transfer_timing,
                 transfer_travel_path, transfer_shoulder_torso_rhythm,
                 do_not_transfer_identity, do_not_transfer_clothing,
                 do_not_transfer_location, do_not_transfer_body_shape,
                 notes, approval_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                shot_id,
                form.get("source_type", "local_path").strip() or "local_path",
                source,
                source_title,
                form.get("owner_license", "").strip(),
                form.get("permitted_use", "").strip(),
                form.get("start_time", "").strip(),
                form.get("end_time", "").strip(),
                form.get("body_framing", "").strip(),
                form.get("travel_direction", "").strip(),
                form.get("speed", "").strip(),
                form.get("face_visibility", "").strip(),
                form.get("rights_status", "").strip(),
                form.get("source_owner_license", "").strip() or form.get("owner_license", "").strip(),
                1 if form.get("transfer_body_movement") == "on" else 0,
                1 if form.get("transfer_timing") == "on" else 0,
                1 if form.get("transfer_travel_path") == "on" else 0,
                1 if form.get("transfer_shoulder_torso_rhythm") == "on" else 0,
                1 if form.get("do_not_transfer_identity") == "on" else 0,
                1 if form.get("do_not_transfer_clothing") == "on" else 0,
                1 if form.get("do_not_transfer_location") == "on" else 0,
                1 if form.get("do_not_transfer_body_shape") == "on" else 0,
                form.get("notes", "").strip(),
                form.get("approval_status", "draft").strip() or "draft",
            ),
        )
        motion_id = int(cursor.lastrowid)
    write_audit(
        "motion_reference_created",
        "motion_references",
        str(motion_id),
        f"Motion reference recorded for {shot_id}.",
        {"shot_id": shot_id, "source_type": form.get("source_type", "local_path"), "approval_status": form.get("approval_status", "draft")},
    )
    return True, "Motion reference recorded. No video was downloaded or copied.", motion_id
