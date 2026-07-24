from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from app.services.audit_service import write_audit
from app.services.db import connect, initialize_database
from app.services.result_import_service import get_result


SCORE_FIELDS = [
    "identity_fidelity",
    "face_safety",
    "natural_body_proportions",
    "movement_realism",
    "choreography_fit",
    "dress_continuity",
    "bar_location_continuity",
    "burmese_cultural_authenticity",
    "camera_composition",
    "lighting",
    "hands_feet_limb_quality",
    "fabric_physics",
    "song_section_usefulness",
    "world_class_readiness",
]

CRITICAL_FIELDS = [
    "no_kung_fu_martial_arts",
    "no_kpop_tiktok_drift",
    "no_karaoke_lounge_staging",
    "no_fake_lipsync",
    "no_microphone_centered",
    "no_fake_body_distortion",
    "no_wrong_dress",
    "no_wrong_venue",
    "no_dangerous_face_failure",
    "normal_speed_review_completed",
]


def _score(value: str) -> int:
    parsed = int(value)
    if parsed < 0 or parsed > 10:
        raise ValueError("score out of range")
    return parsed


def submit_result_review(result_id: int, form: dict[str, str]) -> tuple[bool, str]:
    initialize_database()
    result = get_result(result_id)
    if not result:
        return False, "Unknown result."
    try:
        scores = {field: _score(form.get(field, "")) for field in SCORE_FIELDS}
    except (TypeError, ValueError):
        return False, "All result QC scores must be integers from 0 to 10."

    critical = {field: 1 if form.get(field) == "on" else 0 for field in CRITICAL_FIELDS}
    critical_failure = 0 if all(critical.values()) else 1
    notes = form.get("notes", "").strip()

    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO result_reviews
                (result_id, identity_fidelity, face_safety, natural_body_proportions,
                 movement_realism, choreography_fit, dress_continuity,
                 bar_location_continuity, burmese_cultural_authenticity,
                 camera_composition, lighting, hands_feet_limb_quality,
                 fabric_physics, song_section_usefulness, world_class_readiness,
                 no_kung_fu_martial_arts, no_kpop_tiktok_drift,
                 no_karaoke_lounge_staging, no_fake_lipsync, no_microphone_centered,
                 no_fake_body_distortion, no_wrong_dress, no_wrong_venue,
                 no_dangerous_face_failure, normal_speed_review_completed,
                 critical_failure, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result_id,
                scores["identity_fidelity"],
                scores["face_safety"],
                scores["natural_body_proportions"],
                scores["movement_realism"],
                scores["choreography_fit"],
                scores["dress_continuity"],
                scores["bar_location_continuity"],
                scores["burmese_cultural_authenticity"],
                scores["camera_composition"],
                scores["lighting"],
                scores["hands_feet_limb_quality"],
                scores["fabric_physics"],
                scores["song_section_usefulness"],
                scores["world_class_readiness"],
                critical["no_kung_fu_martial_arts"],
                critical["no_kpop_tiktok_drift"],
                critical["no_karaoke_lounge_staging"],
                critical["no_fake_lipsync"],
                critical["no_microphone_centered"],
                critical["no_fake_body_distortion"],
                critical["no_wrong_dress"],
                critical["no_wrong_venue"],
                critical["no_dangerous_face_failure"],
                critical["normal_speed_review_completed"],
                critical_failure,
                notes,
            ),
        )
        review_id = int(cursor.lastrowid)
        conn.execute("UPDATE imported_results SET status = 'reviewing' WHERE result_id = ?", (result_id,))

    _write_qc_file(result, review_id, scores, critical, critical_failure, notes)
    write_audit(
        "result_qc_reviewed",
        "result_reviews",
        str(review_id),
        f"Result QC submitted for result {result_id}",
        {"result_id": result_id, "critical_failure": critical_failure, **scores},
    )
    return True, "Result QC saved."


def _write_qc_file(result: dict[str, Any], review_id: int, scores: dict[str, int], critical: dict[str, int], critical_failure: int, notes: str) -> None:
    result_dir = Path(result["stored_path"]).parent
    lines = [
        "# QC Result",
        "",
        f"- Review ID: {review_id}",
        f"- Result ID: {result['result_id']}",
        f"- Critical failure: {bool(critical_failure)}",
        "",
        "## Scores",
        "",
    ]
    lines.extend(f"- {field}: {value}/10" for field, value in scores.items())
    lines.extend(["", "## Critical Gates", ""])
    lines.extend(f"- {field}: {'PASS' if value else 'FAIL'}" for field, value in critical.items())
    lines.extend(["", "## Notes", "", notes or "No notes."])
    (result_dir / "QC_RESULT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def latest_review(result_id: int) -> Optional[dict[str, Any]]:
    initialize_database()
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM result_reviews WHERE result_id = ? ORDER BY review_id DESC LIMIT 1",
            (result_id,),
        ).fetchone()
    return dict(row) if row else None
