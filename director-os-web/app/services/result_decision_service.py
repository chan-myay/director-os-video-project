from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.audit_service import write_audit
from app.services.db import connect, initialize_database
from app.services.result_import_service import get_result
from app.services.result_qc_service import latest_review


OUTCOMES = {
    "accept": "accepted",
    "reject": "rejected",
    "needs recut": "needs_recut",
    "needs face correction": "needs_face_correction",
    "archive": "archived",
}

FAILURE_TAGS = {
    "wrong_identity",
    "bad_face",
    "fake_body",
    "bad_limbs",
    "bad_fabric",
    "wrong_dance",
    "kung_fu_drift",
    "kpop_drift",
    "karaoke_drift",
    "fake_lipsync",
    "wrong_dress",
    "wrong_location",
    "weak_motion",
    "repeated_motion",
    "poor_camera",
    "poor_lighting",
    "cultural_drift",
}


def submit_result_decision(result_id: int, form: dict[str, str]) -> tuple[bool, str]:
    initialize_database()
    result = get_result(result_id)
    if not result:
        return False, "Unknown result."
    outcome = form.get("outcome", "").strip()
    if outcome not in OUTCOMES:
        return False, "Invalid decision outcome."

    selected_tags = sorted(tag for tag in FAILURE_TAGS if form.get(tag) == "on")
    reason = form.get("reason", "").strip()
    if outcome == "reject" and not (selected_tags or reason):
        return False, "Rejection requires at least one reason or failure tag."

    review = latest_review(result_id)
    if outcome == "accept" and (not review or review["critical_failure"]):
        return False, "Accepted status is blocked until QC exists with no critical failures."

    usable_time_range = form.get("usable_time_range", "").strip()
    intended_song_section = form.get("intended_song_section", "").strip()
    face_correction_requirement = form.get("face_correction_requirement", "").strip()
    edit_notes = form.get("edit_notes", "").strip()
    status = OUTCOMES[outcome]

    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO result_decisions
                (result_id, outcome, failure_tags, reason, usable_time_range,
                 intended_song_section, face_correction_requirement, edit_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result_id,
                outcome,
                ",".join(selected_tags),
                reason,
                usable_time_range,
                intended_song_section,
                face_correction_requirement,
                edit_notes,
            ),
        )
        decision_id = int(cursor.lastrowid)
        conn.execute("UPDATE imported_results SET status = ? WHERE result_id = ?", (status, result_id))

    _write_decision_file(result, decision_id, outcome, selected_tags, reason, usable_time_range, intended_song_section, face_correction_requirement, edit_notes)
    if outcome == "accept":
        _write_promotion_manifest(result, usable_time_range, intended_song_section, face_correction_requirement, edit_notes)

    write_audit(
        "result_decision_recorded",
        "result_decisions",
        str(decision_id),
        f"Result {result_id} decision: {outcome}",
        {"result_id": result_id, "outcome": outcome, "failure_tags": selected_tags},
    )
    return True, "Result decision saved."


def _write_decision_file(
    result: dict[str, Any],
    decision_id: int,
    outcome: str,
    tags: list[str],
    reason: str,
    usable_time_range: str,
    intended_song_section: str,
    face_correction_requirement: str,
    edit_notes: str,
) -> None:
    result_dir = Path(result["stored_path"]).parent
    text = f"""# Decision

- Decision ID: {decision_id}
- Result ID: {result['result_id']}
- Outcome: {outcome}
- Failure tags: {', '.join(tags) if tags else 'none'}
- Reason: {reason or 'none'}
- Usable time range: {usable_time_range or 'UNKNOWN'}
- Intended song section: {intended_song_section or 'UNKNOWN'}
- Face-correction requirement: {face_correction_requirement or 'UNKNOWN'}

## Edit Notes

{edit_notes or 'No edit notes.'}
"""
    (result_dir / "DECISION.md").write_text(text, encoding="utf-8")


def _write_promotion_manifest(result: dict[str, Any], usable_time_range: str, intended_song_section: str, face_correction_requirement: str, edit_notes: str) -> None:
    result_dir = Path(result["stored_path"]).parent
    text = f"""source_result: {result['stored_path']}
result_id: {result['result_id']}
shot_id: {result['shot_id']}
accepted_usable_time_range: "{usable_time_range}"
intended_song_section: "{intended_song_section}"
face_correction_requirement: "{face_correction_requirement}"
edit_notes: "{edit_notes}"
approval_timestamp: "{result.get('imported_at', '')}"
"""
    (result_dir / "PROMOTION_MANIFEST.yaml").write_text(text, encoding="utf-8")
