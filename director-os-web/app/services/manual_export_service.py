from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.config import ENGINE_ROOT, MANUAL_EXPORT_ROOT
from app.services.audit_service import write_audit
from app.services.db import connect, initialize_database
from app.services.engine_reader import read_text
from app.services.job_service import get_job


EXPORT_STATUSES = {"draft", "blocked", "review_ready", "production_ready", "exported", "superseded"}

BLOCKED_SPEND_TERMS = ("smoke test", "dry-run only", "no upload", "no spend", "unknown")

REQUIRED_EXPORT_FILES = [
    "PRODUCTION_READINESS_REPORT.md",
    "MOTION_REFERENCE_MANIFEST.md",
    "RENDERER_INPUT_MAPPING.md",
    "PLATFORM_SETTINGS.md",
    "FINAL_RENDERER_REQUEST.md",
    "APPROVED_UPLOAD_LIST.md",
    "SPEND_APPROVAL.md",
    "PRIVACY_APPROVAL.md",
    "QC_AFTER_GENERATION.md",
]

EXPORT_FILES = [
    "EXPORT_MANIFEST.yaml",
    "STEP_BY_STEP_UPLOAD_GUIDE.md",
    "REFERENCE_UPLOAD_MANIFEST.md",
    "NEGATIVE_LOCK.md",
    "PRIVACY_WARNING.md",
    "SPEND_LIMIT_NOTE.md",
    "RESULT_IMPORT_INSTRUCTIONS.md",
    "INPUT_MAPPING_SEEDANCE.md",
    "FINAL_SEEDANCE_REQUEST.md",
    "SEEDANCE_SETTINGS.md",
    "INPUT_MAPPING_KLING_MOTION_CONTROL.md",
    "FINAL_KLING_MOTION_CONTROL_REQUEST.md",
    "KLING_SETTINGS.md",
    *REQUIRED_EXPORT_FILES,
    "FINAL_PLATFORM_REQUEST.md",
    "QC_AFTER_GENERATION.md",
]


def list_manual_exports() -> list[dict[str, Any]]:
    initialize_database()
    with connect() as conn:
        rows = conn.execute("SELECT * FROM manual_exports ORDER BY export_id DESC").fetchall()
    return [dict(row) for row in rows]


def get_manual_export(shot_id: str, export_id: int) -> Optional[dict[str, Any]]:
    initialize_database()
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM manual_exports WHERE export_id = ? AND shot_id = ?",
            (export_id, shot_id),
        ).fetchone()
    if not row:
        return None
    export = dict(row)
    try:
        export["missing_requirements_list"] = json.loads(export.get("missing_requirements") or "[]")
    except json.JSONDecodeError:
        export["missing_requirements_list"] = [export.get("missing_requirements", "UNKNOWN")]
    export["readiness_banner"] = (export.get("readiness_status") or export.get("status") or "blocked").upper().replace("_", " ")
    folder = Path(export["export_folder"])
    export["files"] = []
    for file_name in EXPORT_FILES:
        path = folder / file_name
        export["files"].append(
            {
                "name": file_name,
                "path": str(path),
                "content": read_text(path, 12000),
            }
        )
    return export


def create_manual_export(shot_id: str, job_id: int, form: dict[str, str] | str | None = None) -> tuple[bool, str, Optional[int]]:
    initialize_database()
    job = get_job(shot_id, job_id)
    if not job:
        return False, "Unknown job.", None
    if not job["assets"]:
        return False, "Job has no approved reference path records.", None

    if isinstance(form, str):
        form_data = {"notes": form}
    else:
        form_data = form or {}
    notes = form_data.get("notes", "")
    approval = _approval_from_form(job, form_data)
    readiness = evaluate_export_readiness(shot_id, job, approval)

    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO manual_exports
                (job_id, shot_id, renderer, status, export_folder, request_file,
                 reference_manifest, qc_file, notes, approved_renderer,
                 maximum_generation_count, maximum_duration_seconds,
                 maximum_credit_or_currency_spend, exact_cloud_upload_approved,
                 privacy_acknowledged, approval_timestamp, readiness_status,
                 missing_requirements)
            VALUES (?, ?, ?, ?, '', '', '', '', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                shot_id,
                job["renderer"],
                readiness["status"],
                notes,
                approval["approved_renderer"],
                approval["maximum_generation_count"],
                approval["maximum_duration_seconds"],
                approval["maximum_credit_or_currency_spend"],
                1 if approval["exact_cloud_upload_approved"] else 0,
                1 if approval["privacy_acknowledged"] else 0,
                approval["approval_timestamp"],
                readiness["status"],
                json.dumps(readiness["missing_requirements"], sort_keys=True),
            ),
        )
        export_id = int(cursor.lastrowid)
        export_folder = MANUAL_EXPORT_ROOT / shot_id / str(export_id)
        request_file = export_folder / "FINAL_RENDERER_REQUEST.md"
        reference_manifest = export_folder / "REFERENCE_UPLOAD_MANIFEST.md"
        qc_file = export_folder / "QC_AFTER_GENERATION.md"
        conn.execute(
            """
            UPDATE manual_exports
            SET export_folder = ?, request_file = ?, reference_manifest = ?, qc_file = ?
            WHERE export_id = ?
            """,
            (str(export_folder), str(request_file), str(reference_manifest), str(qc_file), export_id),
        )

    _write_export_files(export_id, export_folder, job, notes, approval, readiness)
    write_audit(
        "manual_export_created",
        "manual_exports",
        str(export_id),
        f"Manual export package created for {shot_id} job {job_id}",
        {
            "shot_id": shot_id,
            "job_id": job_id,
            "renderer": job["renderer"],
            "export_folder": str(export_folder),
            "status": readiness["status"],
            "missing_requirements": readiness["missing_requirements"],
        },
    )
    return True, "Manual export package created.", export_id


def _write_export_files(
    export_id: int,
    export_folder: Path,
    job: dict[str, Any],
    notes: str,
    approval: dict[str, Any],
    readiness: dict[str, Any],
) -> None:
    export_folder.mkdir(parents=True, exist_ok=True)
    shot_id = job["shot_id"]
    negative_lock = read_text(ENGINE_ROOT / "generated-requests" / shot_id / "08_NEGATIVE_LOCK.md")

    (export_folder / "EXPORT_MANIFEST.yaml").write_text(_manifest(export_id, job, notes, readiness), encoding="utf-8")
    (export_folder / "STEP_BY_STEP_UPLOAD_GUIDE.md").write_text(_upload_guide(readiness), encoding="utf-8")
    (export_folder / "REFERENCE_UPLOAD_MANIFEST.md").write_text(_reference_manifest(job), encoding="utf-8")
    (export_folder / "NEGATIVE_LOCK.md").write_text(negative_lock, encoding="utf-8")
    (export_folder / "PRIVACY_WARNING.md").write_text(_privacy_warning(), encoding="utf-8")
    (export_folder / "SPEND_LIMIT_NOTE.md").write_text(_spend_limit(job, approval), encoding="utf-8")
    (export_folder / "INPUT_MAPPING_SEEDANCE.md").write_text(_seedance_mapping(job, readiness), encoding="utf-8")
    (export_folder / "FINAL_SEEDANCE_REQUEST.md").write_text(_seedance_request(readiness), encoding="utf-8")
    (export_folder / "SEEDANCE_SETTINGS.md").write_text(_seedance_settings(readiness), encoding="utf-8")
    (export_folder / "INPUT_MAPPING_KLING_MOTION_CONTROL.md").write_text(_kling_mapping(job, readiness), encoding="utf-8")
    (export_folder / "FINAL_KLING_MOTION_CONTROL_REQUEST.md").write_text(_kling_request(readiness), encoding="utf-8")
    (export_folder / "KLING_SETTINGS.md").write_text(_kling_settings(readiness), encoding="utf-8")
    (export_folder / "PRODUCTION_READINESS_REPORT.md").write_text(_production_readiness_report(job, approval, readiness), encoding="utf-8")
    (export_folder / "MOTION_REFERENCE_MANIFEST.md").write_text(_motion_reference_manifest(readiness), encoding="utf-8")
    (export_folder / "RENDERER_INPUT_MAPPING.md").write_text(_renderer_input_mapping(job, readiness), encoding="utf-8")
    (export_folder / "PLATFORM_SETTINGS.md").write_text(_platform_settings(job, readiness), encoding="utf-8")
    (export_folder / "FINAL_RENDERER_REQUEST.md").write_text(_final_renderer_request(job, readiness), encoding="utf-8")
    (export_folder / "FINAL_PLATFORM_REQUEST.md").write_text(_final_renderer_request(job, readiness), encoding="utf-8")
    (export_folder / "APPROVED_UPLOAD_LIST.md").write_text(_approved_upload_list(job, readiness), encoding="utf-8")
    (export_folder / "SPEND_APPROVAL.md").write_text(_spend_approval(approval, readiness), encoding="utf-8")
    (export_folder / "PRIVACY_APPROVAL.md").write_text(_privacy_approval(approval, readiness), encoding="utf-8")
    (export_folder / "QC_AFTER_GENERATION.md").write_text(_qc_after_generation(), encoding="utf-8")
    (export_folder / "RESULT_IMPORT_INSTRUCTIONS.md").write_text(_result_import_instructions(job), encoding="utf-8")


def _manifest(export_id: int, job: dict[str, Any], notes: str, readiness: dict[str, Any]) -> str:
    return f"""export_id: {export_id}
job_id: {job['id']}
shot_id: {job['shot_id']}
renderer_source: {job['renderer']}
status: {readiness['status']}
readiness_status: {readiness['status']}
api_called: false
upload_performed: false
generation_performed: false
media_copied: false
request_file: FINAL_RENDERER_REQUEST.md
reference_manifest: REFERENCE_UPLOAD_MANIFEST.md
qc_file: QC_AFTER_GENERATION.md
missing_requirements: {json.dumps(readiness['missing_requirements'])}
notes: "{notes}"
"""


def _upload_guide(readiness: dict[str, Any]) -> str:
    if readiness["status"] != "production_ready":
        missing = "\n".join(f"- {item}" for item in readiness["missing_requirements"]) or "- UNKNOWN"
        return f"""# Step-By-Step Upload Guide

BLOCKED. Do not open a renderer, upload references, spend credits, or generate.

Missing requirements:

{missing}

Upload instructions are hidden until this export is production_ready.
"""
    return """# Step-By-Step Upload Guide

Manual test order:

1. Open the renderer site manually.
2. Choose image/video generation mode.
3. Upload only the approved references listed in `REFERENCE_UPLOAD_MANIFEST.md`.
4. Paste the matching Seedance or Kling request from `FINAL_PLATFORM_REQUEST.md`.
5. Set duration/format if the renderer offers those controls.
6. Generate one test only.
7. Download the result to a reviewed local folder.
8. Do QC with `QC_AFTER_GENERATION.md` before generating more.

Do not upload child-containing sources, rejected identity sheets, broad private
lead performer/source folders, or any unlisted private media.
"""


def _base_controlled_request() -> str:
    return """Subject: approved adult lead performer performer from the provided approved references only.

Action: sustained side-travel dance across the bar floor.

Framing and camera: medium-wide/full-body side tracking. Keep the face small,
profile, or shadowed. Do not create a clear close face.

Body and wardrobe: natural adult body proportions. Deep red one-shoulder satin
Burmese-inspired dress. Dress movement should be natural during lateral travel.

Location and light: dark teak bar, winter window, amber/crimson lighting,
polished wooden floor, Burmese art/craft world.

Mood and movement: restrained psychological tension and mature blues/jazz
emotional pressure. Grounded posture, controlled shoulders and torso, low
relaxed arms. Choreography must come from the approved motion-reference video,
not from improvised renderer movement.

Hard negatives: no karaoke, no lounge singer, no microphone-centered staging,
no fake singing or lip-sync, no kung fu, no martial arts, no K-pop, no TikTok,
no exaggerated body, no enlarged hips, no enlarged butt, no model-body
reshaping, no warped hands, legs, feet, or fabric. No improvised choreography,
high arm sweeps, fighting shapes, kicks, martial-arts poses, ballet vocabulary
not present in the motion source, spins not present in the motion source, or
front-facing static posing."""


def _seedance_request(readiness: dict[str, Any]) -> str:
    motion = readiness.get("motion_reference")
    motion_line = "Motion reference: MISSING. Do not generate."
    if motion:
        motion_line = (
            f"Motion reference: use {motion['source']} from {motion['start_time']} to {motion['end_time']} "
            f"for body movement, timing, travel path, and shoulder/torso rhythm only."
        )
    request = f"{_base_controlled_request()}\n\n{motion_line}\n"
    return f"""# Final Platform Request

## Seedance

```text
{request.strip()}
```
"""


def _kling_request(readiness: dict[str, Any]) -> str:
    motion = readiness.get("motion_reference")
    plate = readiness.get("character_plate")
    motion_line = "Approved action/motion video: MISSING. Do not generate."
    plate_line = "Approved character/start-frame image: MISSING. Do not generate."
    if motion:
        motion_line = f"Approved action/motion video: {motion['source']} from {motion['start_time']} to {motion['end_time']}."
    if plate:
        plate_line = f"Approved character/start-frame image: {plate['path']}."
    request = f"""{_base_controlled_request()}

{plate_line}
{motion_line}
Use Kling Motion Control to transfer motion only. Preserve the approved
character/start-frame image for performer, dress, bar stage, and lateral floor
space. Use approved A1/A2 face identity only as identity guidance, not as a
separate undifferentiated image pile."""
    return f"""# Final Kling Motion Control Request

```text
{request.strip()}
```
"""


def _reference_manifest(job: dict[str, Any]) -> str:
    lines = [
        "# Reference Upload Manifest",
        "",
        "Upload only these approved file paths manually. This export folder does not contain copied media.",
        "",
        "| Role | File Path | Upload? | Notes |",
        "|---|---|---|---|",
    ]
    for asset in job["assets"]:
        lines.append(f"| {asset['role']} | `{asset['path']}` | yes, manually only | {asset['notes']} |")
    lines.extend(
        [
            "",
            "Do not upload:",
            "",
            "- child-containing sources",
            "- rejected identity sheets",
            "- broad private lead performer/source folders",
            "- unlisted private media",
        ]
    )
    return "\n".join(lines) + "\n"


def _privacy_warning() -> str:
    return """# Privacy Warning

This manual export does not upload anything.

If you later use Seedance, Kling, or another cloud renderer manually, you are
choosing to upload the listed approved references to that third-party service.

Rules:

- Consent is required for real people.
- Do not upload child-containing sources.
- Do not upload rejected lead performer reference sheets.
- Do not upload broad private lead performer/source folders.
- Upload only the exact approved reference files listed in the manifest.
- Stop after one test and review privacy, identity, body, motion, and QC.
"""


def _spend_limit(job: dict[str, Any], approval: dict[str, Any]) -> str:
    return f"""# Spend Limit Note

Recorded job spend/upload limit:

```text
{job['spend_upload_limit']}
```

Structured production approval:

- Approved renderer: {approval['approved_renderer'] or 'MISSING'}
- Maximum generation count: {approval['maximum_generation_count'] or 'MISSING'}
- Maximum duration seconds: {approval['maximum_duration_seconds'] or 'MISSING'}
- Maximum credit/currency spend: {approval['maximum_credit_or_currency_spend'] or 'MISSING'}
- Exact cloud upload approved: {approval['exact_cloud_upload_approved']}
- Approval timestamp: {approval['approval_timestamp'] or 'MISSING'}
"""


def _qc_after_generation() -> str:
    return """# QC After Generation

Use normal-speed playback. Mark each item PASS or FAIL before generating more.

## Critical Fail Conditions

Reject the result immediately if any are true:

- wrong identity
- clear bad face
- fake body proportions
- enlarged hips, enlarged butt, or model-body reshaping
- kung fu, martial arts, K-pop, or TikTok movement
- karaoke, lounge singer, fake lip-sync, or microphone-centered staging
- wrong dress
- wrong bar/location
- warped limbs, hands, feet, or fabric

## Review Sheet

| Item | Pass/Fail | Notes |
|---|---|---|
| lead performer identity from approved references only |  |  |
| Face stays small/profile/shadowed |  |  |
| Natural adult body proportions |  |  |
| Deep red one-shoulder Burmese-inspired dress |  |  |
| Dark teak bar / winter window / amber-crimson lighting |  |  |
| Burmese art/craft world preserved |  |  |
| Sustained side-travel dance across bar floor |  |  |
| Medium-wide/full-body side tracking |  |  |
| Mature blues/jazz tension from approved motion reference |  |  |
| No fake singing/lip-sync |  |  |
| No karaoke/lounge/microphone-centered staging |  |  |
| No kung fu/martial arts/K-pop/TikTok |  |  |
| Hands, feet, legs, and fabric are clean |  |  |
| Worth considering for edit pipeline |  |  |
"""


def _result_import_instructions(job: dict[str, Any]) -> str:
    return f"""# Result Import Instructions

If a manual test is generated later:

1. Save the downloaded result outside this export folder.
2. Do not overwrite existing media.
3. Record renderer, date, settings, and source export ID.
4. Review with `QC_AFTER_GENERATION.md`.
5. Only after QC, decide whether to copy or register the result into the project.

Source job:

- Job ID: {job['id']}
- Shot ID: {job['shot_id']}
- Renderer source: {job['renderer']}

No result has been generated by Director OS v0.6A.
"""


def _approval_from_form(job: dict[str, Any], form: dict[str, str]) -> dict[str, Any]:
    return {
        "approved_renderer": form.get("approved_renderer", job["renderer"]).strip(),
        "maximum_generation_count": _int_value(form.get("maximum_generation_count", "")),
        "maximum_duration_seconds": _float_value(form.get("maximum_duration_seconds", "")),
        "maximum_credit_or_currency_spend": form.get("maximum_credit_or_currency_spend", "").strip(),
        "exact_cloud_upload_approved": form.get("exact_cloud_upload_approved") == "on",
        "privacy_acknowledged": form.get("privacy_acknowledged") == "on",
        "approval_timestamp": form.get("approval_timestamp", "").strip() or datetime.now(timezone.utc).isoformat(),
    }


def _int_value(value: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _float_value(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def evaluate_export_readiness(shot_id: str, job: dict[str, Any], approval: dict[str, Any]) -> dict[str, Any]:
    renderer = (approval["approved_renderer"] or job["renderer"] or "").lower()
    missing: list[str] = []
    warnings: list[str] = []
    spend_text = " ".join(
        [
            str(job.get("spend_upload_limit", "")),
            str(approval.get("maximum_credit_or_currency_spend", "")),
        ]
    ).lower()
    if any(term in spend_text for term in BLOCKED_SPEND_TERMS) or not approval["maximum_credit_or_currency_spend"].strip():
        missing.append("INVALID_SMOKE_TEST_SPEND_GATE")
    if not approval["approved_renderer"]:
        missing.append("MISSING_APPROVED_RENDERER")
    if approval["maximum_generation_count"] <= 0:
        missing.append("MISSING_MAXIMUM_GENERATION_COUNT")
    if approval["maximum_duration_seconds"] <= 0:
        missing.append("MISSING_MAXIMUM_DURATION_SECONDS")
    if not approval["exact_cloud_upload_approved"]:
        missing.append("MISSING_EXACT_CLOUD_UPLOAD_APPROVAL")
    if not approval["privacy_acknowledged"]:
        missing.append("MISSING_PRIVACY_ACKNOWLEDGEMENT")
    if not approval["approval_timestamp"]:
        missing.append("MISSING_APPROVAL_TIMESTAMP")

    motion_reference = _approved_motion_reference(shot_id)
    if not motion_reference:
        missing.append("MISSING_MOTION_REFERENCE")
    else:
        motion_missing = _motion_reference_missing(motion_reference)
        missing.extend(motion_missing)

    character_plate = None
    if "kling" in renderer:
        character_plate = _approved_character_plate(shot_id)
        if not character_plate:
            missing.append("MISSING_CHARACTER_START_FRAME")
            missing.append("KLING_CHARACTER_START_FRAME_NOT_APPROVED")

    if "seedance" in renderer and not motion_reference:
        missing.append("SEEDANCE_MOTION_REFERENCE_REQUIRED")
    if "kling" not in renderer and "seedance" not in renderer:
        warnings.append("UNKNOWN_RENDERER_SPECIALIZATION")

    missing = sorted(set(missing))
    status = "production_ready" if not missing else "blocked"
    if status == "blocked" and not any(item.startswith("INVALID") or item.startswith("MISSING") for item in missing):
        status = "review_ready"
    return {
        "status": status,
        "renderer": renderer,
        "missing_requirements": missing,
        "warnings": warnings,
        "motion_reference": motion_reference,
        "character_plate": character_plate,
    }


def _approved_motion_reference(shot_id: str) -> Optional[dict[str, Any]]:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT * FROM motion_references
            WHERE shot_id = ? AND approval_status = 'approved'
            ORDER BY motion_id DESC
            LIMIT 1
            """,
            (shot_id,),
        ).fetchone()
    return dict(row) if row else None


def _motion_reference_missing(motion: dict[str, Any]) -> list[str]:
    missing = []
    if not motion["source"]:
        missing.append("MOTION_REFERENCE_SOURCE_MISSING")
    if not motion["start_time"] or not motion["end_time"]:
        missing.append("MOTION_REFERENCE_TIMECODE_MISSING")
    if motion["travel_direction"] not in {"left-to-right", "right-to-left"}:
        missing.append("MOTION_REFERENCE_DIRECTION_INVALID")
    if motion["body_framing"] not in {"full-body", "medium-wide"}:
        missing.append("MOTION_REFERENCE_FRAMING_INVALID")
    if not motion["rights_status"] or not motion["source_owner_license"]:
        missing.append("MOTION_REFERENCE_RIGHTS_MISSING")
    for field, code in [
        ("transfer_body_movement", "MOTION_TRANSFER_BODY_MOVEMENT_MISSING"),
        ("transfer_timing", "MOTION_TRANSFER_TIMING_MISSING"),
        ("transfer_travel_path", "MOTION_TRANSFER_TRAVEL_PATH_MISSING"),
        ("transfer_shoulder_torso_rhythm", "MOTION_TRANSFER_SHOULDER_TORSO_MISSING"),
        ("do_not_transfer_identity", "MOTION_DO_NOT_TRANSFER_IDENTITY_MISSING"),
        ("do_not_transfer_clothing", "MOTION_DO_NOT_TRANSFER_CLOTHING_MISSING"),
        ("do_not_transfer_location", "MOTION_DO_NOT_TRANSFER_LOCATION_MISSING"),
        ("do_not_transfer_body_shape", "MOTION_DO_NOT_TRANSFER_BODY_SHAPE_MISSING"),
    ]:
        if not motion[field]:
            missing.append(code)
    return missing


def _approved_character_plate(shot_id: str) -> Optional[dict[str, Any]]:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT * FROM character_plates
            WHERE shot_id = ?
              AND role = 'character_start_frame'
              AND approval_status = 'approved'
              AND full_body_performer = 1
              AND correct_deep_red_dress = 1
              AND correct_bar_stage = 1
              AND lateral_floor_space = 1
              AND body_scale_matches_motion = 1
              AND no_children = 1
              AND approved_identity_state = 1
            ORDER BY plate_id DESC
            LIMIT 1
            """,
            (shot_id,),
        ).fetchone()
    return dict(row) if row else None


def _asset_by_role(job: dict[str, Any], role: str) -> str:
    for asset in job["assets"]:
        if asset["role"] == role:
            return asset["path"]
    return "MISSING"


def _motion_reference_manifest(readiness: dict[str, Any]) -> str:
    motion = readiness.get("motion_reference")
    if not motion:
        return "# Motion Reference Manifest\n\nMISSING_MOTION_REFERENCE\n"
    return f"""# Motion Reference Manifest

- Source: {motion['source']}
- Source title: {motion['source_title']}
- Owner/license: {motion['source_owner_license']}
- Rights status: {motion['rights_status']}
- Permitted use: {motion['permitted_use']}
- Usable timecode: {motion['start_time']} to {motion['end_time']}
- Travel direction: {motion['travel_direction']}
- Body framing: {motion['body_framing']}
- Speed: {motion['speed']}
- Face visibility: {motion['face_visibility']}
- Transfer: body movement, timing, travel path, shoulder/torso rhythm
- Do not transfer: source person identity, clothing, location, body shape
"""


def _seedance_mapping(job: dict[str, Any], readiness: dict[str, Any]) -> str:
    motion = readiness.get("motion_reference")
    return f"""# Seedance Input Mapping

Use the platform attachment labels generated by Seedance UI/API. Do not assume
all uploaded files have the same role.

| Required Input | File/Source | Role |
|---|---|---|
| identity front | {_asset_by_role(job, 'identity_front')} | identity reference |
| identity three-quarter | {_asset_by_role(job, 'identity_threequarter')} | identity reference |
| body/wardrobe | {_asset_by_role(job, 'wardrobe_body')} | body and dress reference |
| bar/stage | {_asset_by_role(job, 'bar_stage')} | location reference |
| Burmese art world | {_asset_by_role(job, 'burmese_art_world')} | cultural world reference |
| motion-reference video | {motion['source'] if motion else 'MISSING'} | action/motion reference |

Blocked unless motion-reference video is approved.
"""


def _kling_mapping(job: dict[str, Any], readiness: dict[str, Any]) -> str:
    motion = readiness.get("motion_reference")
    plate = readiness.get("character_plate")
    return f"""# Kling Motion Control Input Mapping

Do not upload all five stills as undifferentiated references. Kling Motion
Control requires specialized roles.

| Required Input | File/Source | Role |
|---|---|---|
| approved character/start-frame image | {plate['path'] if plate else 'MISSING_CHARACTER_START_FRAME'} | character_start_frame |
| approved action/motion video | {motion['source'] if motion else 'MISSING_MOTION_REFERENCE'} | action/motion source |
| approved identity face element | {_asset_by_role(job, 'identity_front')} and {_asset_by_role(job, 'identity_threequarter')} | identity guidance |
| character orientation mode | side/profile lateral travel | orientation control |
| camera behavior | medium-wide side tracking | camera control |
| motion-transfer instructions | transfer body movement, timing, travel path, shoulder/torso rhythm only | motion control |
"""


def _renderer_input_mapping(job: dict[str, Any], readiness: dict[str, Any]) -> str:
    if "kling" in readiness["renderer"]:
        return _kling_mapping(job, readiness)
    if "seedance" in readiness["renderer"]:
        return _seedance_mapping(job, readiness)
    return "# Renderer Input Mapping\n\nUNKNOWN_RENDERER_SPECIALIZATION\n"


def _seedance_settings(readiness: dict[str, Any]) -> str:
    return f"""# Seedance Settings

- Renderer: Seedance
- Duration: from structured spend approval only
- Format: choose video generation mode with reference attachments
- Motion source required: {bool(readiness.get('motion_reference'))}
- Real generation readiness: {readiness['status'] == 'production_ready'}
"""


def _kling_settings(readiness: dict[str, Any]) -> str:
    return f"""# Kling Motion Control Settings

- Renderer: Kling Motion Control
- Character orientation mode: side/profile lateral travel
- Camera behavior: medium-wide side tracking
- Character start frame required: {bool(readiness.get('character_plate'))}
- Motion video required: {bool(readiness.get('motion_reference'))}
- Real generation readiness: {readiness['status'] == 'production_ready'}
"""


def _platform_settings(job: dict[str, Any], readiness: dict[str, Any]) -> str:
    if "kling" in readiness["renderer"]:
        return _kling_settings(readiness)
    if "seedance" in readiness["renderer"]:
        return _seedance_settings(readiness)
    return f"# Platform Settings\n\nRenderer `{job['renderer']}` is not specialized for production export.\n"


def _final_renderer_request(job: dict[str, Any], readiness: dict[str, Any]) -> str:
    if "kling" in readiness["renderer"]:
        return _kling_request(readiness)
    if "seedance" in readiness["renderer"]:
        return _seedance_request(readiness)
    return "# Final Renderer Request\n\nUNKNOWN_RENDERER_SPECIALIZATION\n"


def _approved_upload_list(job: dict[str, Any], readiness: dict[str, Any]) -> str:
    lines = ["# Approved Upload List", "", "No media is copied into this export folder.", ""]
    if "seedance" in readiness["renderer"]:
        lines.append(_seedance_mapping(job, readiness))
    elif "kling" in readiness["renderer"]:
        lines.append(_kling_mapping(job, readiness))
    else:
        lines.append("UNKNOWN_RENDERER_SPECIALIZATION")
    return "\n".join(lines) + "\n"


def _spend_approval(approval: dict[str, Any], readiness: dict[str, Any]) -> str:
    return f"""# Spend Approval

- Approved renderer: {approval['approved_renderer'] or 'MISSING'}
- Maximum generation count: {approval['maximum_generation_count']}
- Maximum duration seconds: {approval['maximum_duration_seconds']}
- Maximum credit/currency spend: {approval['maximum_credit_or_currency_spend'] or 'MISSING'}
- Production-ready spend gate: {readiness['status'] == 'production_ready'}
"""


def _privacy_approval(approval: dict[str, Any], readiness: dict[str, Any]) -> str:
    return f"""# Privacy Approval

- Exact cloud upload approved: {approval['exact_cloud_upload_approved']}
- Privacy acknowledged: {approval['privacy_acknowledged']}
- Approval timestamp: {approval['approval_timestamp'] or 'MISSING'}
- Production-ready privacy gate: {readiness['status'] == 'production_ready'}
"""


def _production_readiness_report(job: dict[str, Any], approval: dict[str, Any], readiness: dict[str, Any]) -> str:
    missing = "\n".join(f"- {item}" for item in readiness["missing_requirements"]) or "- none"
    return f"""# Production Readiness Report

- Shot ID: {job['shot_id']}
- Job ID: {job['id']}
- Renderer: {readiness['renderer']}
- Readiness status: {readiness['status']}
- API called: false
- Upload performed: false
- Generation performed: false
- Media copied: false

## Missing Requirements

{missing}

## Renderer-Specific Result

- Seedance requires identity front, identity three-quarter, body/wardrobe,
  bar/stage, Burmese art world, and approved motion-reference video.
- Kling Motion Control requires an approved character/start-frame image,
  approved action/motion video, A1/A2 identity guidance, character orientation
  mode, camera behavior, and motion-transfer instructions.

## Structured Approval

- Approved renderer: {approval['approved_renderer'] or 'MISSING'}
- Maximum generation count: {approval['maximum_generation_count']}
- Maximum duration seconds: {approval['maximum_duration_seconds']}
- Maximum credit/currency spend: {approval['maximum_credit_or_currency_spend'] or 'MISSING'}
- Exact cloud upload approved: {approval['exact_cloud_upload_approved']}
- Privacy acknowledged: {approval['privacy_acknowledged']}
- Approval timestamp: {approval['approval_timestamp'] or 'MISSING'}
"""


def correct_existing_export_three() -> None:
    initialize_database()
    reasons = [
        "INVALID_SMOKE_TEST_SPEND_GATE",
        "MISSING_MOTION_REFERENCE",
        "RENDERER_PACKAGE_NOT_SPECIALIZED",
        "KLING_CHARACTER_START_FRAME_NOT_APPROVED",
    ]
    with connect() as conn:
        row = conn.execute("SELECT * FROM manual_exports WHERE export_id = 3").fetchone()
        if not row:
            return
        current = dict(row)
        if current.get("status") == "superseded" and current.get("missing_requirements"):
            return
        notes = (current.get("notes") or "").strip()
        if notes:
            notes += "\n"
        notes += "v0.6A.1 correction: " + ", ".join(reasons)
        conn.execute(
            """
            UPDATE manual_exports
            SET status = 'superseded',
                readiness_status = 'blocked',
                missing_requirements = ?,
                notes = ?
            WHERE export_id = 3
            """,
            (json.dumps(reasons, sort_keys=True), notes),
        )
    write_audit(
        "manual_export_superseded",
        "manual_exports",
        "3",
        "Export #3 marked superseded by v0.6A.1 readiness enforcement.",
        {"reasons": reasons},
    )
