from __future__ import annotations

from typing import Any, Optional

from app.services.db import connect, initialize_database


CHILD_CONTAINING_SOURCES = [
    "references/My lead performer/IMG_5930.MOV",
    "references/My lead performer/IMG_6737.MOV",
    "references/My lead performer/IMG_6742.MOV",
]

REJECTED_REFERENCE_MARKERS = [
    "references/rejected/",
    "REF-A_PERFORMER-IDENTITY-3ANGLE",
    "REJECTED",
    "SIMSWAP512",
]

BROAD_PRIVATE_MARKERS = [
    "references/My lead performer",
    "references/My lead performer/",
    "My lead performer/",
]

F01_REQUIRED_REFERENCES = {
    "identity_front": "references/approved/REF-A1_PERFORMER-FACE-FRONT_APPROVED.png",
    "identity_threequarter": "references/approved/REF-A2_PERFORMER-FACE-THREEQUARTER_APPROVED.png",
    "wardrobe_body": "references/approved/REF-B_PERFORMER-WARDROBE-FULLBODY_APPROVED.png",
    "bar_stage": "references/approved/REF-C_BAR-STAGE_APPROVED.png",
    "burmese_art_world": "references/approved/REF-E_BURMESE-ART-INSERTS_APPROVED.png",
}


def reference_lines(reference_text: str) -> list[str]:
    lines = []
    for raw in reference_text.splitlines():
        value = raw.strip().strip("-").strip()
        if value:
            lines.append(value)
    return lines


def latest_approved_gate(shot_pack_id: int, renderer: str) -> Optional[dict[str, Any]]:
    initialize_database()
    with connect() as conn:
        row = conn.execute(
            """
            SELECT * FROM approval_gates
            WHERE shot_pack_id = ?
              AND renderer_selected = ?
              AND decision = 'approve'
              AND privacy_warning_acknowledged = 1
              AND final_request_reviewed = 1
            ORDER BY id DESC
            LIMIT 1
            """,
            (shot_pack_id, renderer),
        ).fetchone()
    return dict(row) if row else None


def connector_record(renderer: str) -> Optional[dict[str, Any]]:
    initialize_database()
    with connect() as conn:
        row = conn.execute("SELECT * FROM connector_status WHERE name = ?", (renderer,)).fetchone()
    return dict(row) if row else None


def required_references_for_shot(shot_id: str) -> dict[str, str]:
    if shot_id == "F01_side_travel_dance":
        return dict(F01_REQUIRED_REFERENCES)
    return {}


def reference_completeness(shot_id: str, references: list[str]) -> dict[str, Any]:
    required = required_references_for_shot(shot_id)
    present = {}
    missing = {}
    for role, required_path in required.items():
        matched = any(required_path in ref for ref in references)
        if matched:
            present[role] = required_path
        else:
            missing[role] = required_path
    return {
        "required": required,
        "present": present,
        "missing": missing,
        "complete": not missing,
    }


def evaluate_asset_policy(
    shot_pack_id: int,
    shot_id: str,
    renderer: str,
    spend_upload_limit: str,
    privacy_acknowledged: bool,
    references_text: str,
) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []
    references = reference_lines(references_text)

    if not spend_upload_limit.strip():
        blockers.append("spend/upload limit is missing")
    if not privacy_acknowledged:
        blockers.append("privacy acknowledgement is missing")

    approved = latest_approved_gate(shot_pack_id, renderer)
    if not approved:
        blockers.append("no matching approved approval gate for this shot pack and renderer")

    connector = connector_record(renderer)
    if not connector:
        blockers.append("renderer connector is unknown")
    elif not connector["enabled"]:
        blockers.append("connector disabled; real generation is blocked in v0.5.1")

    if not references:
        blockers.append("exact approved references are missing")

    completeness = reference_completeness(shot_id, references)
    if not completeness["complete"]:
        for role, required_path in completeness["missing"].items():
            blockers.append(f"required reference missing for {role}: {required_path}")

    for ref in references:
        if any(child in ref for child in CHILD_CONTAINING_SOURCES):
            blockers.append(f"child-containing source referenced: {ref}")
        if any(marker in ref for marker in REJECTED_REFERENCE_MARKERS):
            blockers.append(f"rejected reference marker found: {ref}")
        if any(marker in ref for marker in BROAD_PRIVATE_MARKERS) and not ref.endswith((".png", ".jpg", ".jpeg", ".heic.png", ".HEIC.png")):
            blockers.append(f"broad private lead performer/source folder referenced: {ref}")

    if connector and not connector["local_possible"]:
        warnings.append("cloud/manual renderer would require upload approval later; v0.5 dry-run does not upload")
    if connector and connector["private_media_risk"]:
        warnings.append(f"private media risk: {connector['private_media_risk']}")

    return {
        "blocked": bool(blockers),
        "blockers": blockers,
        "warnings": warnings,
        "references": references,
        "reference_completeness": completeness,
        "real_generation_readiness": not blockers,
        "approval": approved,
        "connector": connector,
    }
