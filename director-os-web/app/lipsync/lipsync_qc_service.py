from __future__ import annotations

from typing import Any

from app.lipsync.schemas import CRITICAL_FAILURES
from app.services.db import connect, initialize_database


SCORE_FIELDS = [
    "sync_accuracy",
    "identity_consistency",
    "face_quality",
    "temporal_consistency",
    "expression_naturalness",
    "body_motion_naturalness",
    "background_preservation",
    "edit_usability",
]


def save_lipsync_review(output_id: int, form: dict[str, str]) -> tuple[bool, str]:
    initialize_database()
    scores = {}
    for field in SCORE_FIELDS:
        try:
            scores[field] = max(0, min(10, int(form.get(field, "0"))))
        except ValueError:
            return False, f"Invalid score for {field}."
    failures = [tag for tag in CRITICAL_FAILURES if form.get(tag) == "on"]
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO lipsync_reviews
                (output_id, sync_accuracy, identity_consistency, face_quality,
                 temporal_consistency, expression_naturalness, body_motion_naturalness,
                 background_preservation, edit_usability, critical_failures,
                 normal_speed_review_completed, frame_level_review_completed, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                output_id,
                scores["sync_accuracy"],
                scores["identity_consistency"],
                scores["face_quality"],
                scores["temporal_consistency"],
                scores["expression_naturalness"],
                scores["body_motion_naturalness"],
                scores["background_preservation"],
                scores["edit_usability"],
                ",".join(failures),
                1 if form.get("normal_speed_review_completed") == "on" else 0,
                1 if form.get("frame_level_review_completed") == "on" else 0,
                form.get("notes", ""),
            ),
        )
    return True, "Lip-sync review saved."


def list_lipsync_reviews(output_id: int) -> list[dict[str, Any]]:
    initialize_database()
    with connect() as conn:
        rows = conn.execute("SELECT * FROM lipsync_reviews WHERE output_id = ? ORDER BY review_id DESC", (output_id,)).fetchall()
    return [dict(row) for row in rows]
