#!/usr/bin/env python3
from __future__ import annotations

import os
import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path


WEB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = WEB_ROOT.parent
TEST_DB = WEB_ROOT / "data" / "director_os_test.sqlite"
DEV_DB = WEB_ROOT / "data" / "director_os.sqlite"
TEST_RESULT_MEDIA = WEB_ROOT / "result-media-test"
TEST_STORYBOARD_MODEL_ROOT = WEB_ROOT / "test-output" / "storyboard-model"
TEST_STORYBOARD_VARIANT_ROOT = WEB_ROOT / "test-output" / "storyboard-variants"
os.environ["DIRECTOR_OS_DATABASE"] = str(TEST_DB)
os.environ["DIRECTOR_OS_RESULT_MEDIA_ROOT"] = str(TEST_RESULT_MEDIA)
os.environ["DIRECTOR_OS_INTELLIGENCE_PROVIDER"] = "mock"
os.environ["DIRECTOR_OS_DISABLE_NETWORK"] = "1"
os.environ["DIRECTOR_OS_STORYBOARD_MODEL_ROOT"] = str(TEST_STORYBOARD_MODEL_ROOT)
os.environ["DIRECTOR_OS_STORYBOARD_VARIANT_ROOT"] = str(TEST_STORYBOARD_VARIANT_ROOT)
sys.path.insert(0, str(WEB_ROOT))

from app.config import DATABASE_PATH  # noqa: E402
from app.services.approval_service import create_approval  # noqa: E402
from app.services.db import initialize_database  # noqa: E402
from app.services.director_workspace_service import (  # noqa: E402
    build_animatic,
    comment_storyboard_card,
    create_voice_test,
    decide_storyboard_card,
    list_caption_lines,
    list_storyboard_cards,
    sync_workspace_from_latest_plan,
    workspace_summary,
)
from app.services.job_service import create_job, get_job, run_job_dry_run  # noqa: E402
from app.services.manual_export_service import create_manual_export, get_manual_export  # noqa: E402
from app.services.media_probe_service import find_binary  # noqa: E402
from app.services.result_decision_service import submit_result_decision  # noqa: E402
from app.services.result_import_service import get_result, import_result_from_path  # noqa: E402
from app.services.result_qc_service import submit_result_review  # noqa: E402
from app.services.workflow_service import connector_records, seed_from_existing_files, workflow_summary  # noqa: E402
from app.services.v09_studio_service import create_autonomous_run, run_autonomous_studio, run_status  # noqa: E402
from app.services.setup_decision_service import list_setup_decisions, record_setup_decision  # noqa: E402
from app.services.storyboard_model_service import (  # noqa: E402
    generate_storyboard_ai_variant,
    record_storyboard_model_decision,
    run_fake_storyboard_benchmark,
    storyboard_model_decision_context,
)
from app.system_tools.tool_health import system_tool_health  # noqa: E402
from app.services.local_capability_service import run_local_capability_audit  # noqa: E402
from app.services.burmese_language_service import build_burmese_timeline  # noqa: E402
from app.services.lipsync_service import build_lipsync_plan, create_lipsync_job, create_manual_infinitetalk_export, refresh_lipsync_provider_health  # noqa: E402
from app.services.lyric_timing_service import build_lyric_timing_authority, lyric_timing_summary  # noqa: E402
from app.services.provider_control_service import provider_capacity_status, resume_provider_run  # noqa: E402
from app.burmese.zawgyi_unicode_service import zawgyi_to_unicode, converter_status  # noqa: E402
from app.audio.auto_sync_service import auto_sync_lyrics, font_render_preview, rebuild_caption_v4  # noqa: E402
from app.audio.brain_sync_service import (  # noqa: E402
    brain_lipsync_readiness,
    build_animatic_v15,
    build_brain_timeline,
    rebuild_caption_v5,
    rebuild_caption_v6,
    run_local_asr_alignment,
)
from app.audio.sync_offset_service import generate_offset_candidates, sync_calibration_status  # noqa: E402
from app.services.latest_safe_animatic_service import latest_safe_animatic_context, resolve_director_asset  # noqa: E402


EXPECTED_TABLES = {
    "projects",
    "shot_packs",
    "generated_requests",
    "approval_gates",
    "qc_reviews",
    "connector_status",
    "reference_moodboards",
    "audit_logs",
    "generation_jobs",
    "job_assets",
    "job_events",
    "job_outputs",
    "manual_exports",
    "motion_references",
    "character_plates",
    "imported_results",
    "result_media",
    "result_reviews",
    "result_decisions",
    "director_runs",
    "storyboard_cards",
    "storyboard_decisions",
    "storyboard_comments",
    "previs_assets",
    "motion_reference_analysis",
    "burmese_caption_lines",
    "lyric_source_lines",
    "lyric_phrases",
    "voice_audio_assets",
    "voice_phrase_alignments",
    "pronunciation_overrides",
    "voice_tests",
    "animatics",
    "renderer_strategy_items",
    "research_items",
    "autonomous_runs",
    "autonomous_run_stages",
    "autonomous_run_events",
    "visual_grammar",
    "local_backend_status",
    "setup_decisions",
    "local_capability_records",
    "local_model_records",
    "local_benchmarks",
    "storyboard_model_installations",
    "storyboard_model_benchmarks",
    "storyboard_ai_variants",
    "lipsync_jobs",
    "lipsync_job_inputs",
    "lipsync_outputs",
    "lipsync_reviews",
    "lipsync_decisions",
    "lipsync_provider_health",
    "lipsync_audio_segments",
}


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def table_names() -> set[str]:
    with sqlite3.connect(str(DATABASE_PATH)) as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {row[0] for row in rows}


def dev_counts() -> dict[str, int]:
    if not DEV_DB.exists():
        return {}
    with sqlite3.connect(str(DEV_DB)) as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        counts = {}
        for (table,) in rows:
            if table.startswith("sqlite_"):
                continue
            counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    return counts


def create_tiny_video(path: Path) -> None:
    ffmpeg = find_binary("ffmpeg")
    assert_true(ffmpeg is not None, "ffmpeg not found for smoke test")
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=160x90:rate=12:duration=1",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def assert_zawgyi_fixtures() -> None:
    fixtures = json.loads((WEB_ROOT / "app" / "burmese" / "fixtures" / "zawgyi_conversion_fixtures.json").read_text(encoding="utf-8"))
    for fixture in fixtures:
        if fixture["expected_detection"] == "zawgyi":
            result = zawgyi_to_unicode(fixture["source"], confidence=1.0)
            assert_true(result["converted"] == fixture["expected_unicode"], f"Zawgyi fixture failed: {fixture['name']}")
            assert_true(result["status"] in {"converted_validated", "conversion_needs_review"}, f"invalid conversion status for {fixture['name']}")
        else:
            assert_true(fixture["source"] == fixture["expected_unicode"], f"Unicode no-op fixture invalid: {fixture['name']}")


def main() -> int:
    before_dev = dev_counts()
    if TEST_DB.exists():
        TEST_DB.unlink()
    if TEST_RESULT_MEDIA.exists():
        shutil.rmtree(str(TEST_RESULT_MEDIA))
    if TEST_STORYBOARD_MODEL_ROOT.exists():
        shutil.rmtree(str(TEST_STORYBOARD_MODEL_ROOT))
    if TEST_STORYBOARD_VARIANT_ROOT.exists():
        shutil.rmtree(str(TEST_STORYBOARD_VARIANT_ROOT))

    initialize_database()
    seed_from_existing_files()
    assert_true(converter_status()["active"] in {"icu_transliterator_Zawgyi-my", "pyicu_transliterator_Zawgyi-my", "director_os_local_rule_zawgyi_converter"}, "converter status missing active engine")
    assert_zawgyi_fixtures()
    summary = workflow_summary()
    connectors = connector_records()

    assert_true(str(DATABASE_PATH) == str(TEST_DB), "smoke test is not using test database")
    assert_true(TEST_DB.exists(), "test database file was not created")
    assert_true(EXPECTED_TABLES.issubset(table_names()), "one or more required tables are missing")
    assert_true(summary["counts"]["shot_packs"] >= 7, "shot packs were not seeded")
    assert_true(any(shot["shot_id"] == "F01_side_travel_dance" for shot in summary["shot_packs"]), "F01 was not seeded")
    assert_true(summary["counts"]["generated_requests"] >= 11, "generated F01 requests were not seeded")
    assert_true(len(connectors) >= 7, "connector stubs were not seeded")
    assert_true(all(record["enabled"] == 0 for record in connectors), "all connector stubs must remain disabled")

    workspace = sync_workspace_from_latest_plan()
    assert_true(workspace["card_count"] >= 24, "storyboard workspace was not populated")
    assert_true(workspace["previs_count"] >= 24, "raster previs assets were not created")
    cards = list_storyboard_cards()
    assert_true(cards and cards[0]["raster_path"].endswith(".png"), "storyboard cards do not reference PNG previs")
    assert_true(Path(cards[0]["raster_path"]).exists(), "PNG previs file missing")
    ok, message = decide_storyboard_card(cards[0]["shot_number"], "approved", "Smoke test approval.")
    assert_true(ok, f"storyboard decision failed: {message}")
    ok, message = comment_storyboard_card(cards[0]["shot_number"], "Smoke test comment.")
    assert_true(ok, f"storyboard comment failed: {message}")
    workspace = workspace_summary()
    assert_true(workspace["approved"] >= 1, "storyboard approval was not persisted")
    assert_true(workspace["comments"] >= 1, "storyboard comment was not persisted")
    animatic = build_animatic()
    assert_true(Path(animatic["path"]).exists(), "animatic html missing")
    caption_lines = list_caption_lines()
    assert_true(len(caption_lines) > 0, "Burmese caption workspace was not seeded")
    ok, message = create_voice_test(
        {
            "provider": "manual",
            "voice_name": "smoke-test-manual",
            "input_text": caption_lines[0]["caption_text"],
            "pronunciation_notes": "No API call; local planning record only.",
            "consent_confirmed": "on",
        }
    )
    assert_true(ok, f"voice test record failed: {message}")

    run_id = create_autonomous_run("Smoke test one-command autonomous studio run.", str(REPO_ROOT))
    run_result = run_autonomous_studio(run_id, use_provider=True, timeout=20)
    assert_true(run_result["run"]["run_id"] == run_id, "v0.9 run status missing run id")
    assert_true(run_result["completed_stages"] >= 17, "v0.9 staged run did not complete all stages with mock provider")
    assert_true(run_result["run"]["status"] == "ready_with_approvals", "optional setup should produce ready_with_approvals, not blocked")
    assert_true("LOCAL_STORYBOARD_MODEL_REQUIRED" in run_result["blockers"], "local AI image backend blocker missing")
    assert_true("VOICE_PROVIDER_NOT_CONFIGURED" in run_result["blockers"], "voice provider blocker missing")
    assert_true(not run_result["blocker_groups"]["hard_blockers"], "optional setup was incorrectly classified as hard blocker")
    assert_true(
        any(item["code"] == "LOCAL_STORYBOARD_MODEL_REQUIRED" for item in run_result["blocker_groups"]["approvals_needed"]),
        "storyboard model blocker was not classified as approval required",
    )
    assert_true(
        any(item["code"] == "VOICE_PROVIDER_NOT_CONFIGURED" for item in run_result["blocker_groups"]["optional_capabilities"]),
        "voice provider blocker was not classified as optional capability",
    )
    with sqlite3.connect(str(TEST_DB)) as conn:
        grammar_count = conn.execute("SELECT COUNT(*) FROM visual_grammar").fetchone()[0]
        research_count = conn.execute("SELECT COUNT(*) FROM research_items").fetchone()[0]
        stage_count = conn.execute("SELECT COUNT(*) FROM autonomous_run_stages WHERE run_id = ?", (run_id,)).fetchone()[0]
        research_statuses = {row[0] for row in conn.execute("SELECT DISTINCT verification_status FROM research_items").fetchall()}
    assert_true(grammar_count >= 24, "visual grammar was not populated")
    assert_true(research_count >= 10, "automatic research leads were not stored")
    assert_true("search_suggestion_only" in research_statuses, "research verification status was not persisted")
    assert_true(stage_count == 17, "unexpected staged run count")
    tool_health = system_tool_health()
    assert_true(tool_health["ffmpeg"]["found"], "ffmpeg health check failed")
    assert_true(tool_health["ffprobe"]["found"], "ffprobe health check failed")
    animatic_dir = REPO_ROOT / "director-os" / "animatics" / str(run_id)
    metadata_path = animatic_dir / "MEDIA_METADATA.json"
    assert_true((animatic_dir / "ANIMATIC.mp4").exists(), "MP4 animatic was not created")
    assert_true(metadata_path.exists(), "MP4 media metadata was not written")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert_true(metadata.get("clean", {}).get("video_codec") == "h264", "MP4 animatic video codec was not validated")
    assert_true(metadata.get("clean", {}).get("audio_codec") == "aac", "MP4 animatic audio codec was not validated")
    record_setup_decision("storyboard_model", "continue_composite_previs", "Smoke test: no model install.")
    record_setup_decision("burmese_voice", "caption_only", "Smoke test: no cloud voice call.")
    decisions = list_setup_decisions()
    assert_true(any(row["decision_type"] == "storyboard_model" for row in decisions), "storyboard setup decision was not persisted")
    assert_true(any(row["decision_type"] == "burmese_voice" for row in decisions), "voice setup decision was not persisted")
    model_setup = storyboard_model_decision_context()
    assert_true(model_setup["real_project_ai_frame_count"] == 0, "real AI frame count must be zero before local model install")
    assert_true(not model_setup["downloads_performed"], "model setup must not report downloads before approval")
    primary_commands = model_setup["primary"]["commands"]
    assert_true(primary_commands and all(isinstance(command, list) for command in primary_commands), "install commands must be argument arrays")
    approval = record_storyboard_model_decision("approve_primary", "Smoke test approval record only; no download.")
    assert_true(approval["installer_package"], "storyboard approval did not create an install package")
    assert_true(not approval["downloaded"], "approval must not download model files")
    installer = Path(approval["installer_package"])
    assert_true((installer / "INSTALL_PLAN.md").exists(), "install plan missing")
    assert_true((installer / "COMMANDS.json").exists(), "command manifest missing")
    commands = json.loads((installer / "COMMANDS.json").read_text(encoding="utf-8"))
    assert_true(all(isinstance(command, list) for command in commands), "stored install commands must be argument arrays")
    blocked_ok, blocked_message, _blocked_variant = generate_storyboard_ai_variant(
        cards[0]["shot_number"],
        "Move the performer toward the right third, retain cold negative space near the winter window, remove background people, keep arms below shoulder height, and strengthen the warm practical lighting.",
    )
    assert_true(not blocked_ok and "LOCAL_STORYBOARD_MODEL_REQUIRED" in blocked_message, "real local generation must block without an operational model")
    benchmark = run_fake_storyboard_benchmark()
    assert_true(Path(benchmark["output_path"]).exists(), "fake benchmark output missing")
    assert_true(benchmark["origin_label"] == "PLACEHOLDER", "fake benchmark must not be labeled as local AI generated")
    variant_ok, variant_message, variant = generate_storyboard_ai_variant(
        cards[0]["shot_number"],
        "Move the performer toward the right third, retain cold negative space near the winter window, remove background people, keep arms below shoulder height, and strengthen the warm practical lighting.",
        fake_backend=True,
    )
    assert_true(variant_ok, f"fake storyboard variant failed: {variant_message}")
    assert_true(Path(variant["image_path"]).exists(), "fake storyboard variant image missing")
    assert_true(variant["origin_label"] == "PLACEHOLDER", "fake storyboard variant must not claim real AI generation")
    assert_true(variant["no_upload"] and variant["no_api"], "fake storyboard variant must not upload or call APIs")
    with sqlite3.connect(str(TEST_DB)) as conn:
        variant_count = conn.execute("SELECT COUNT(*) FROM storyboard_ai_variants WHERE shot_number = ?", (cards[0]["shot_number"],)).fetchone()[0]
        other_variant_count = conn.execute("SELECT COUNT(*) FROM storyboard_ai_variants WHERE shot_number <> ?", (cards[0]["shot_number"],)).fetchone()[0]
    assert_true(variant_count == 1 and other_variant_count == 0, "storyboard varianting must affect only one shot")
    capabilities = run_local_capability_audit()
    assert_true(any(item["name"] == "mp4_animatic" for item in capabilities["matrix"]["capabilities"]), "local capability matrix missing mp4 animatic")
    assert_true((REPO_ROOT / "director-os/state/LOCAL_CAPABILITY_MATRIX.json").exists(), "local capability matrix state file missing")
    burmese = build_burmese_timeline()
    assert_true(burmese["original_preserved"], "Burmese original text preservation flag missing")
    timing = build_lyric_timing_authority()
    timing_summary = lyric_timing_summary()
    assert_true(timing["summary"]["lyric_phrase_count"] > 0, "lyric timing authority did not create phrases")
    assert_true(timing_summary["locked_count"] == timing_summary["phrase_count"], "all phrase timings should be locked for lip-sync")
    auto_sync = auto_sync_lyrics()
    assert_true(auto_sync["auto_synced_phrase_count"] == timing_summary["phrase_count"], "auto-sync did not create phrase suggestions")
    assert_true(auto_sync["status"] == "auto_boundary_unverified", "auto-sync must remain review/unverified before human listening")
    assert_true(auto_sync["low_confidence_phrase_count"] > 0, "boundary-only sync must not be treated as high confidence")
    font_preview = font_render_preview()
    assert_true(Path(font_preview["font_sample"]).exists(), "Burmese font sample preview missing")
    assert_true(Path(font_preview["caption_overlay_sample"]).exists(), "caption overlay preview missing")
    caption_v4 = rebuild_caption_v4()
    assert_true(caption_v4["review_caption_count"] == timing_summary["phrase_count"], "caption v4 review export did not include phrase suggestions")
    assert_true(any("AUTO_SYNC_LOW_CONFIDENCE" in blocker for blocker in caption_v4["blockers"]), "caption v4 did not block low-confidence auto sync")
    brain = build_brain_timeline()
    assert_true(brain["version"] == "v1.0.6", "brain timeline version missing")
    assert_true(brain["offset"]["global_caption_delay_seconds"] >= 0, "brain timeline offset missing")
    assert_true(brain["sync_method_counts"], "brain timeline did not record sync method counts")
    assert_true((REPO_ROOT / "director-os/state/PRODUCTION_BRAIN_TIMELINE.json").exists(), "brain timeline state file missing")
    caption_v5 = rebuild_caption_v5()
    assert_true(caption_v5["review_caption_count"] == timing_summary["phrase_count"], "caption v5 review export did not include brain-sync phrases")
    assert_true(any("BRAIN_SYNC_LOW_CONFIDENCE" in blocker for blocker in caption_v5["blockers"]), "caption v5 did not block low-confidence brain sync")
    candidates = generate_offset_candidates()
    assert_true(candidates["candidates"], "sync calibration did not produce offset candidates")
    assert_true(candidates["best_candidate"]["offset_seconds"] is not None, "sync calibration did not select a candidate")
    calibration = sync_calibration_status()
    assert_true(calibration["proposed_offset_seconds"] is not None, "sync calibration status missing proposed offset")
    asr = run_local_asr_alignment()
    assert_true(asr["classification"] in {"asr_unavailable", "asr_timing_useful_text_uncertain"}, "ASR classification invalid")
    caption_v6 = rebuild_caption_v6()
    assert_true(caption_v6["review_caption_count"] == timing_summary["phrase_count"], "caption v6 review export did not include calibrated phrases")
    assert_true(any("SYNC_CALIBRATION_LOW_CONFIDENCE" in blocker for blocker in caption_v6["blockers"]), "caption v6 did not block low-confidence calibration")
    run15 = build_animatic_v15()
    assert_true(run15["duration_validation"]["status"] in {"ok", "warning"}, "Run 15 duration validation failed")
    assert_true(Path(run15["run_dir"], "ANIMATIC_WITH_CAPTIONS_SYNC_CALIBRATED_REVIEW.mp4").exists(), "Run 15 captioned review MP4 missing")
    brain_ready = brain_lipsync_readiness()
    assert_true(brain_ready["ready_count"] == 0, "low-confidence brain sync must not make lip-sync ready")
    assert_true(brain_ready["blocked_count"] > 0, "brain lip-sync readiness did not report blockers")
    latest = latest_safe_animatic_context()
    assert_true("latest_version" in latest, "latest safe animatic context missing version")
    old_path, old_status, _ = resolve_director_asset("animatics/11/ANIMATIC_WITH_CAPTIONS.mp4")
    if old_path is not None:
        assert_true(old_status == 200, "existing old Run 11 media should still be serveable")
    missing_path, missing_status, _ = resolve_director_asset("animatics/13/DOES_NOT_EXIST.mp4")
    assert_true(missing_path is None and missing_status == 404, "missing animatic media must return a useful 404")
    traversal_path, traversal_status, _ = resolve_director_asset("../START-HERE-TOMORROW.md")
    assert_true(traversal_path is None and traversal_status == 403, "director asset traversal must be blocked")
    assert_true((REPO_ROOT / "director-os/captions/final-timing/CAPTIONS_FINAL_TIMING.srt").exists(), "final timing SRT missing")
    assert_true((REPO_ROOT / "director-os/captions/final-timing/CAPTIONS_FINAL_TIMING.vtt").exists(), "final timing VTT missing")
    assert_true((REPO_ROOT / "director-os/captions/final-timing/CAPTIONS_FINAL_TIMING.ass").exists(), "final timing ASS missing")
    lipsync_plan = build_lipsync_plan(run_id)
    assert_true(len(lipsync_plan["eligibility"]) >= 24, "lip-sync eligibility map missing shots")
    assert_true(any(item.get("phrase_id") for item in lipsync_plan["eligibility"]), "lip-sync plan did not link to lyric phrases")
    providers = refresh_lipsync_provider_health()
    assert_true(any(provider["provider"] == "manual_infinitetalk" for provider in providers), "manual InfiniteTalk provider missing")
    lip_job_id = create_lipsync_job("S01")
    ok, message, package_path = create_manual_infinitetalk_export(lip_job_id)
    assert_true(ok, f"manual InfiniteTalk package failed: {message}")
    package = Path(package_path)
    assert_true((package / "INFINITETALK_JOB_MANIFEST.yaml").exists(), "InfiniteTalk package manifest missing")
    assert_true((package / "LYRIC_TIMING.md").exists(), "InfiniteTalk lyric timing link missing")
    assert_true("UNKNOWN lyric line" not in (package / "LYRIC_TIMING.md").read_text(encoding="utf-8"), "lip-sync package still uses unknown lyric placeholder")
    assert_true(not list(package.glob("*.mp4")), "manual InfiniteTalk package must not copy video media")
    provider_summary = provider_capacity_status()
    assert_true("health" in provider_summary, "provider status missing health")
    resume_summary = resume_provider_run(run_id)
    assert_true("fallback_marked_stages" in resume_summary, "resume-provider-run summary missing stages")

    ok, message = create_approval(
        "F01_side_travel_dance",
        {
            "renderer_selected": "seedance",
            "exact_references": "\n".join(
                [
                    "references/approved/REF-A1_WIFE-FACE-FRONT_APPROVED.png",
                    "references/approved/REF-A2_WIFE-FACE-THREEQUARTER_APPROVED.png",
                    "references/approved/REF-B_WIFE-WARDROBE-FULLBODY_APPROVED.png",
                    "references/approved/REF-C_BAR-STAGE_APPROVED.png",
                    "references/approved/REF-E_BURMESE-ART-INSERTS_APPROVED.png",
                ]
            ),
            "spend_upload_limit": "smoke test dry-run only; no upload; no spend",
            "decision": "approve",
            "privacy_warning_acknowledged": "on",
            "final_request_reviewed": "on",
            "notes": "Smoke-test approval for local dry-run package only.",
        },
    )
    assert_true(ok, f"approval creation failed: {message}")

    ok, message, job_id = create_job(
        "F01_side_travel_dance",
        {
            "renderer": "seedance",
            "request_filename": "05_SEEDANCE_REQUEST.md",
            "spend_upload_limit": "smoke test dry-run only; no upload; no spend",
            "privacy_acknowledged": "on",
        },
    )
    assert_true(ok and job_id is not None, f"job creation failed: {message}")
    ok, message = run_job_dry_run("F01_side_travel_dance", int(job_id))
    assert_true(ok, f"dry-run failed: {message}")

    ok, message, export_id = create_manual_export("F01_side_travel_dance", int(job_id), "Smoke-test export.")
    assert_true(ok and export_id is not None, f"manual export creation failed: {message}")
    export = get_manual_export("F01_side_travel_dance", int(export_id))
    assert_true(export is not None, "manual export could not be loaded")
    assert_true(export["readiness_status"] == "blocked", "smoke-test spend gate must not become production_ready")
    assert_true("INVALID_SMOKE_TEST_SPEND_GATE" in export["missing_requirements_list"], "smoke-test spend blocker missing")
    assert_true("MISSING_MOTION_REFERENCE" in export["missing_requirements_list"], "F01 without motion video must be blocked")
    seedance_dir = Path(export["export_folder"])
    assert_true((seedance_dir / "PRODUCTION_READINESS_REPORT.md").exists(), "production readiness report missing")
    assert_true((seedance_dir / "MOTION_REFERENCE_MANIFEST.md").exists(), "motion reference manifest missing")
    assert_true((seedance_dir / "INPUT_MAPPING_SEEDANCE.md").exists(), "Seedance input mapping missing")
    assert_true((seedance_dir / "FINAL_SEEDANCE_REQUEST.md").exists(), "Seedance final request missing")
    assert_true((seedance_dir / "STEP_BY_STEP_UPLOAD_GUIDE.md").read_text(encoding="utf-8").startswith("# Step-By-Step Upload Guide\n\nBLOCKED"), "blocked export exposed upload instructions")

    ok, message = create_approval(
        "F01_side_travel_dance",
        {
            "renderer_selected": "kling",
            "exact_references": "\n".join(
                [
                    "references/approved/REF-A1_WIFE-FACE-FRONT_APPROVED.png",
                    "references/approved/REF-A2_WIFE-FACE-THREEQUARTER_APPROVED.png",
                    "references/approved/REF-B_WIFE-WARDROBE-FULLBODY_APPROVED.png",
                    "references/approved/REF-C_BAR-STAGE_APPROVED.png",
                    "references/approved/REF-E_BURMESE-ART-INSERTS_APPROVED.png",
                ]
            ),
            "spend_upload_limit": "smoke test dry-run only; no upload; no spend",
            "decision": "approve",
            "privacy_warning_acknowledged": "on",
            "final_request_reviewed": "on",
            "notes": "Smoke-test Kling approval for local dry-run package only.",
        },
    )
    assert_true(ok, f"kling approval creation failed: {message}")
    ok, message, kling_job_id = create_job(
        "F01_side_travel_dance",
        {
            "renderer": "kling",
            "request_filename": "04_KLING_REQUEST.md",
            "spend_upload_limit": "smoke test dry-run only; no upload; no spend",
            "privacy_acknowledged": "on",
        },
    )
    assert_true(ok and kling_job_id is not None, f"kling job creation failed: {message}")
    ok, message, kling_export_id = create_manual_export(
        "F01_side_travel_dance",
        int(kling_job_id),
        {
            "approved_renderer": "kling",
            "maximum_generation_count": "1",
            "maximum_duration_seconds": "5",
            "maximum_credit_or_currency_spend": "smoke test dry-run only; no upload; no spend",
            "exact_cloud_upload_approved": "on",
            "privacy_acknowledged": "on",
            "notes": "Kling blocked-readiness smoke export.",
        },
    )
    assert_true(ok and kling_export_id is not None, f"kling export creation failed: {message}")
    kling_export = get_manual_export("F01_side_travel_dance", int(kling_export_id))
    assert_true(kling_export is not None, "kling export could not be loaded")
    assert_true("MISSING_MOTION_REFERENCE" in kling_export["missing_requirements_list"], "Kling without motion video must be blocked")
    assert_true("KLING_CHARACTER_START_FRAME_NOT_APPROVED" in kling_export["missing_requirements_list"], "Kling without character start frame must be blocked")
    kling_dir = Path(kling_export["export_folder"])
    seedance_mapping = (seedance_dir / "INPUT_MAPPING_SEEDANCE.md").read_text(encoding="utf-8")
    kling_mapping = (kling_dir / "INPUT_MAPPING_KLING_MOTION_CONTROL.md").read_text(encoding="utf-8")
    assert_true(seedance_mapping != kling_mapping, "Seedance and Kling mappings must be different")
    copied_media = list(seedance_dir.glob("*.mp4")) + list(seedance_dir.glob("*.mov")) + list(seedance_dir.glob("*.webm")) + list(seedance_dir.glob("*.png")) + list(seedance_dir.glob("*.jpg"))
    copied_media += list(kling_dir.glob("*.mp4")) + list(kling_dir.glob("*.mov")) + list(kling_dir.glob("*.webm")) + list(kling_dir.glob("*.png")) + list(kling_dir.glob("*.jpg"))
    assert_true(not copied_media, "manual export folders must not contain copied media")

    source_video = WEB_ROOT / "data" / "smoke-test-generated-result.mp4"
    create_tiny_video(source_video)
    ok, message, result_id = import_result_from_path(
        str(source_video),
        "F01_side_travel_dance",
        int(job_id),
        int(export_id),
        "seedance",
        is_test=True,
    )
    assert_true(ok and result_id is not None, f"result import failed: {message}")
    result = get_result(int(result_id))
    assert_true(result is not None, "imported result could not be loaded")
    assert_true(result["duration"] > 0, "duration was not probed")
    assert_true(result["width"] == 160 and result["height"] == 90, "dimensions were not probed")
    result_dir = Path(result["stored_path"]).parent
    assert_true((result_dir / "metadata.json").exists(), "metadata.json missing")
    assert_true((result_dir / "poster.jpg").exists(), "poster missing")
    assert_true((result_dir / "contact-sheet.jpg").exists(), "contact sheet missing")

    score_form = {field: "5" for field in [
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
    ]}
    score_form.update({"normal_speed_review_completed": "on", "notes": "Smoke test QC with intentional critical failures."})
    ok, message = submit_result_review(int(result_id), score_form)
    assert_true(ok, f"result QC failed: {message}")

    ok, message = submit_result_decision(
        int(result_id),
        {
            "outcome": "reject",
            "wrong_dance": "on",
            "weak_motion": "on",
            "reason": "Synthetic smoke-test video is not a real generation.",
        },
    )
    assert_true(ok, f"result decision failed: {message}")
    result = get_result(int(result_id))
    assert_true(result["status"] == "rejected", "result was not rejected")
    assert_true((result_dir / "QC_RESULT.md").exists(), "QC_RESULT.md missing")
    assert_true((result_dir / "DECISION.md").exists(), "DECISION.md missing")

    with sqlite3.connect(str(TEST_DB)) as conn:
        audit_count = conn.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0]
    assert_true(audit_count >= 5, "audit events were not written")
    assert_true(before_dev == dev_counts(), "normal development database counts changed during smoke test")

    print("smoke ok")
    print(f"test_database: {DATABASE_PATH}")
    print(f"dry_run_job: {job_id}")
    print(f"manual_export: {export_id}")
    print(f"kling_manual_export: {kling_export_id}")
    print(f"result_id: {result_id}")
    print(f"result_dir: {result_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
