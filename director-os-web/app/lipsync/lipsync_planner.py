from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import ENGINE_ROOT
from app.lipsync.provider_registry import refresh_lipsync_provider_health
from app.lipsync.shot_eligibility_service import classify_lipsync_shots
from app.services.db import connect, initialize_database
from app.services.lyric_timing_service import build_lyric_timing_authority, extract_lipsync_audio_for_phrase, phrase_for_shot_time


def build_lipsync_plan(run_id: int = 9) -> dict[str, Any]:
    initialize_database()
    build_lyric_timing_authority()
    root = ENGINE_ROOT / "lipsync" / str(run_id)
    root.mkdir(parents=True, exist_ok=True)
    eligibility = classify_lipsync_shots()
    provider_health = refresh_lipsync_provider_health()
    plan = {
        "run_id": run_id,
        "eligibility": eligibility,
        "provider_health": provider_health,
        "policy": {
            "audio_authoritative": True,
            "no_runpod_submission_without_approval": True,
            "no_lipsync_for_wide_dance_silhouette_or_object_inserts": True,
            "face_correction_order": [
                "lock source clip and edit timing",
                "create lip-sync output",
                "perform lip-sync QC",
                "perform identity QC",
                "apply HiFiFace/UniFace only when required",
                "rerun lip-sync QC after face correction",
            ],
        },
    }
    (root / "LIPSYNC_ELIGIBILITY_MAP.json").write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (root / "LIPSYNC_PLAN.md").write_text(render_plan_markdown(plan), encoding="utf-8")
    seed_lipsync_jobs(run_id, eligibility)
    return plan


def seed_lipsync_jobs(run_id: int, eligibility: list[dict[str, Any]]) -> None:
    with connect() as conn:
        for item in eligibility:
            if item["eligibility"] not in {"lipsync_required", "lipsync_optional"}:
                continue
            conn.execute(
                """
                INSERT INTO lipsync_jobs
                    (run_id, shot_id, status, provider, mode, eligibility, blocked_reasons)
                VALUES (?, ?, 'planned', 'manual_infinitetalk', 'video_to_video', ?, ?)
                """,
                (run_id, item["shot_id"], item["eligibility"], "EDIT_LOCK_REQUIRED,EXACT_UPLOAD_APPROVAL_REQUIRED,SPEND_APPROVAL_REQUIRED"),
            )


def create_lipsync_job(shot_id: str, run_id: int = 9) -> int:
    initialize_database()
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO lipsync_jobs
                (run_id, shot_id, status, provider, mode, eligibility, blocked_reasons)
            VALUES (?, ?, 'planned', 'manual_infinitetalk', 'video_to_video', 'manual_review_required',
                    'EDIT_LOCK_REQUIRED,EXACT_UPLOAD_APPROVAL_REQUIRED,SPEND_APPROVAL_REQUIRED')
            """,
            (run_id, shot_id),
        )
        return int(cursor.lastrowid)


def list_lipsync_jobs() -> list[dict[str, Any]]:
    initialize_database()
    with connect() as conn:
        rows = conn.execute("SELECT * FROM lipsync_jobs ORDER BY job_id DESC").fetchall()
    return [dict(row) for row in rows]


def get_lipsync_job(job_id: int) -> dict[str, Any] | None:
    initialize_database()
    with connect() as conn:
        row = conn.execute("SELECT * FROM lipsync_jobs WHERE job_id = ?", (job_id,)).fetchone()
    return dict(row) if row else None


def create_manual_infinitetalk_export(job_id: int) -> tuple[bool, str, str]:
    job = get_lipsync_job(job_id)
    if not job:
        return False, "Unknown lip-sync job.", ""
    root = ENGINE_ROOT / "manual-exports" / "lipsync" / job["shot_id"] / str(job_id)
    root.mkdir(parents=True, exist_ok=True)
    phrase = phrase_for_lipsync_job(job)
    if not phrase:
        return False, "No lyric phrase timing is available. Build the Burmese lyric timing authority first.", ""
    audio = extract_lipsync_audio_for_phrase(job["run_id"] or 9, job["shot_id"], phrase)
    files = {
        "INFINITETALK_JOB_MANIFEST.yaml": render_manifest(job, audio),
        "RUNPOD_UPLOAD_LIST.md": upload_list(job, audio),
        "VIDEO_INPUT.md": "# Video Input\n\nSource video is not copied. Select the exact edit-locked source clip manually.\n",
        "AUDIO_INPUT.md": f"# Audio Input\n\nFull mix segment: `{audio['full_mix_segment']}`\nVocal segment: `{audio['vocal_segment']}`\n",
        "LYRIC_TIMING.md": lyric_timing_doc(phrase, audio),
        "INFINITETALK_SETTINGS.md": settings_doc(),
        "FINAL_INFINITETALK_REQUEST.md": final_request(job),
        "PRIVACY_APPROVAL.md": privacy_doc(),
        "SPEND_APPROVAL.md": spend_doc(),
        "DOWNLOAD_AND_IMPORT_GUIDE.md": import_guide(),
        "LIPSYNC_QC.md": qc_doc(),
    }
    for name, text in files.items():
        (root / name).write_text(text, encoding="utf-8")
    with connect() as conn:
        conn.execute(
            "UPDATE lipsync_jobs SET package_path = ?, audio_segment_path = ?, full_mix_segment_path = ?, updated_at = CURRENT_TIMESTAMP WHERE job_id = ?",
            (str(root), audio["vocal_segment"], audio["full_mix_segment"], job_id),
        )
    return True, "Manual InfiniteTalk package created. No upload or API call occurred.", str(root)


def phrase_for_lipsync_job(job: dict[str, Any]) -> dict[str, Any] | None:
    eligibility = classify_lipsync_shots()
    match = next((item for item in eligibility if item["shot_id"] == job["shot_id"]), None)
    if match and match.get("phrase_id"):
        phrase = phrase_for_shot_time(float(match.get("phrase_start") or 0), float(match.get("phrase_end") or 0))
        if phrase:
            return phrase
    return phrase_for_shot_time(0, 5)


def render_plan_markdown(plan: dict[str, Any]) -> str:
    lines = ["# Lip-Sync Plan", "", "## Eligibility", ""]
    for item in plan["eligibility"]:
        lines.append(f"- `{item['shot_id']}`: {item['eligibility']} - {item['recommended_method']}")
    lines.extend(["", "## Policy", "", "- InfiniteTalk is a lip-sync/performance tool, not a movement generator for F01.", "- No RunPod/API submission without exact upload, spend and endpoint approval."])
    return "\n".join(lines) + "\n"


def render_manifest(job: dict[str, Any], audio: dict[str, Any]) -> str:
    return f"""shot_id: {job['shot_id']}
job_id: {job['job_id']}
provider: manual_infinitetalk
mode: video_to_video
audio_authoritative: true
phrase_id: {audio.get('phrase_id', 0)}
phrase_index: {audio.get('phrase_index', 0)}
timing_source: {audio.get('timing_source', '')}
vocal_segment: {audio['vocal_segment']}
full_mix_segment: {audio['full_mix_segment']}
no_api_call: true
no_upload: true
"""


def lyric_timing_doc(phrase: dict[str, Any], audio: dict[str, Any]) -> str:
    return f"""# Lyric Timing

Phrase ID: `{phrase['phrase_id']}`
Phrase index: `{phrase['phrase_index']}`
Timing source: `{phrase['final_timing_source']}`
Timing locked for lip-sync: `{bool(phrase['lipsync_timing_locked'])}`

Start: `{phrase['final_start_time']:.3f}`
End: `{phrase['final_end_time']:.3f}`

Original Burmese:
{phrase['original_text']}

Normalized Unicode:
{phrase['normalized_unicode']}

Pronunciation helper:
{phrase['pronunciation_helper']}

Caption:
{phrase['caption_text']}

Audio segment:
- Full mix: `{audio['full_mix_segment']}`
- Vocal/reference: `{audio['vocal_segment']}`

The actual audio segment is authoritative. Text is for review, diagnostics and caption/lip-sync linking only.
"""


def upload_list(job: dict[str, Any], audio: dict[str, Any]) -> str:
    return f"""# RunPod Upload List

Upload nothing until privacy and spend approval are recorded.

Allowed after approval:
- exact edit-locked source video for `{job['shot_id']}`
- `{audio['full_mix_segment']}`
- `{audio['vocal_segment']}`

Never upload broad private folders, child-containing media, rejected identity sheets, or unrelated assets.
"""


def settings_doc() -> str:
    return "# InfiniteTalk Settings\n\nMode: video-to-video dubbing. Preserve source background/camera. Use actual approved song segment as audio authority.\n"


def final_request(job: dict[str, Any]) -> str:
    return f"# Final InfiniteTalk Request\n\nCreate lip-sync only for shot `{job['shot_id']}`. Preserve identity, background, camera and body motion. Do not change choreography. Use approved audio segment as authoritative timing.\n"


def privacy_doc() -> str:
    return "# Privacy Approval\n\nRequired before any RunPod upload. No approval is recorded by this package.\n"


def spend_doc() -> str:
    return "# Spend Approval\n\nRequired before any paid RunPod execution. No approval is recorded by this package.\n"


def import_guide() -> str:
    return "# Download And Import Guide\n\nAfter manual generation, download the result locally and import through Director OS result/lip-sync QC. Do not overwrite source media.\n"


def qc_doc() -> str:
    return "# Lip-Sync QC\n\nReview normal speed and frame-by-frame. Reject wrong identity, mouth deformation, audio offset, face melting, flicker, body deformation or broken background.\n"
