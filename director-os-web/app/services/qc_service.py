from __future__ import annotations

from typing import Any

from app.services.audit_service import write_audit
from app.services.db import connect, initialize_database
from app.services.workflow_service import get_shot_pack_record


VALID_QC_DECISIONS = {"pass", "fail", "needs recut", "needs face correction", "needs new generation"}
SCORE_FIELDS = [
    "identity_score",
    "face_risk_score",
    "body_risk_score",
    "motion_score",
    "cultural_authenticity_score",
    "world_class_score",
]


def _parse_score(value: str) -> int:
    score = int(value)
    if score < 0 or score > 10:
        raise ValueError("score out of range")
    return score


def list_qc_reviews(shot_id: str) -> list[dict[str, Any]]:
    initialize_database()
    shot = get_shot_pack_record(shot_id)
    if not shot:
        return []
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM qc_reviews WHERE shot_pack_id = ? ORDER BY id DESC",
            (shot["id"],),
        ).fetchall()
    return [dict(row) for row in rows]


def create_qc_review(shot_id: str, form: dict[str, str]) -> tuple[bool, str]:
    initialize_database()
    shot = get_shot_pack_record(shot_id)
    if not shot:
        return False, "Unknown shot pack."

    decision = form.get("decision", "").strip()
    notes = form.get("notes", "").strip()
    if decision not in VALID_QC_DECISIONS:
        return False, "Invalid QC decision."

    try:
        scores = {field: _parse_score(form.get(field, "")) for field in SCORE_FIELDS}
    except (TypeError, ValueError):
        return False, "All QC scores must be integers from 0 to 10."

    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO qc_reviews
                (shot_pack_id, decision, notes, identity_score, face_risk_score,
                 body_risk_score, motion_score, cultural_authenticity_score,
                 world_class_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                shot["id"],
                decision,
                notes,
                scores["identity_score"],
                scores["face_risk_score"],
                scores["body_risk_score"],
                scores["motion_score"],
                scores["cultural_authenticity_score"],
                scores["world_class_score"],
            ),
        )
        qc_id = cursor.lastrowid

    write_audit(
        "qc_review_recorded",
        "qc_reviews",
        str(qc_id),
        f"QC decision '{decision}' recorded for {shot_id}",
        {"shot_id": shot_id, "decision": decision, **scores},
    )
    return True, "QC review recorded."
