#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

WEB_ROOT = Path(__file__).resolve().parents[2]
if str(WEB_ROOT) not in sys.path:
    sys.path.insert(0, str(WEB_ROOT))

from app.services.autonomous_director_service import (  # noqa: E402
    DEFAULT_IDEA,
    director_status,
    research_search_assistant,
    run_autonomous_director,
    write_research_audit,
)
from app.services.db import initialize_database  # noqa: E402
from app.services.director_workspace_service import build_animatic, sync_workspace_from_latest_plan, workspace_summary  # noqa: E402
from app.services.workflow_service import seed_from_existing_files  # noqa: E402
from app.services.v09_studio_service import build_edit_handoff, create_autonomous_run, run_autonomous_studio, run_status, list_runs  # noqa: E402
from app.services.provider_control_service import provider_capacity_status, resume_provider_run  # noqa: E402
from app.services.local_capability_service import local_capability_summary, run_local_capability_audit  # noqa: E402
from app.services.lipsync_service import build_lipsync_plan, create_lipsync_job, create_manual_infinitetalk_export, list_lipsync_jobs  # noqa: E402
from app.services.burmese_language_service import build_burmese_timeline, burmese_language_summary  # noqa: E402
from app.services.director_workspace_service import analyze_motion_reference  # noqa: E402
from app.burmese.zawgyi_unicode_service import converter_status, zawgyi_to_unicode  # noqa: E402
from app.services.lyric_timing_service import (  # noqa: E402
    conversion_review_summary,
    import_voice_audio_for_phrase,
    lipsync_readiness_summary,
    rebuild_caption_v2,
    validate_phrase_timing,
    voice_sync_summary,
)
from app.services.v104_animatic_sync_service import (  # noqa: E402
    animatic_reality_audit,
    font_check,
    listening_sync_status,
    music_analysis,
)
from app.audio.auto_sync_service import (  # noqa: E402
    auto_sync_lyrics,
    auto_sync_status,
    build_animatic_v13,
    font_render_preview,
    rebuild_caption_v4,
    v105_caption_readiness,
    v105_lipsync_readiness,
)
from app.audio.brain_sync_service import (  # noqa: E402
    apply_caption_offset,
    approve_global_caption_offset,
    brain_lipsync_readiness,
    brain_timeline_status,
    build_animatic_v15,
    build_animatic_v14,
    build_brain_timeline,
    build_calibrated_brain_timeline,
    rebuild_caption_v6,
    rebuild_caption_v5,
    run_local_asr_alignment,
)
from app.audio.asr.asr_health import asr_health  # noqa: E402
from app.audio.sync_offset_service import generate_offset_candidates, sync_calibration_status  # noqa: E402
from app.services.latest_safe_animatic_service import diagnose_animatic_route  # noqa: E402
from app.studio_loop.orchestrator import (  # noqa: E402
    DEFAULT_STUDIO_IDEA,
    cancel_studio_loop,
    continue_studio_loop,
    create_studio_loop,
    latest_loop,
    run_studio_loop,
    studio_loop_detail,
    studio_loop_report,
    studio_loop_status,
)
from app.audio_truth.orchestrator import run_audio_truth_v24, run_audio_truth_v241  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(prog="director-os", description="Autonomous Director OS local CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create", help="Create an autonomous director plan from one idea")
    create.add_argument("idea", nargs="?", default=DEFAULT_IDEA)
    create.add_argument("--project", default=str(WEB_ROOT.parent))

    for name in ["continue", "analyze", "storyboard", "plan-production", "status", "concepts", "voice-test", "local-capabilities"]:
        p = sub.add_parser(name)
        p.add_argument("project", nargs="?", default=str(WEB_ROOT.parent))
        if name in {"status", "local-capabilities"}:
            p.add_argument("--json", action="store_true")

    provider = sub.add_parser("provider-status")
    provider.add_argument("--json", action="store_true")

    resume = sub.add_parser("resume-provider-run")
    resume.add_argument("run_id", type=int)

    motion = sub.add_parser("motion-analyze")
    motion.add_argument("video_path")

    lipsync_plan = sub.add_parser("lipsync-plan")
    lipsync_plan.add_argument("project", nargs="?", default=str(WEB_ROOT.parent))
    lipsync_status = sub.add_parser("lipsync-status")
    lipsync_status.add_argument("project", nargs="?", default=str(WEB_ROOT.parent))
    lipsync_export = sub.add_parser("lipsync-export")
    lipsync_export.add_argument("shot_id")
    lipsync_import = sub.add_parser("lipsync-import")
    lipsync_import.add_argument("result_path")
    lipsync_import.add_argument("--shot", required=True)
    lipsync_qc = sub.add_parser("lipsync-qc")
    lipsync_qc.add_argument("result_id", type=int)
    lipsync_submit = sub.add_parser("lipsync-submit-runpod")
    lipsync_submit.add_argument("job_id", type=int)

    sub.add_parser("burmese-converter-status")
    sub.add_parser("burmese-conversion-review-status")
    burmese_convert = sub.add_parser("burmese-convert")
    burmese_convert.add_argument("file")
    burmese_convert.add_argument("--preview", action="store_true")
    rebuild_captions = sub.add_parser("rebuild-captions")
    rebuild_captions.add_argument("project", nargs="?", default=str(WEB_ROOT.parent))
    rebuild_captions.add_argument("--version", default="v2")
    rebuild_captions.add_argument("--auto-sync", action="store_true")
    rebuild_captions.add_argument("--brain-sync", action="store_true")
    rebuild_captions.add_argument("--sync-calibrated", action="store_true")
    align_status = sub.add_parser("lyric-alignment-status")
    align_status.add_argument("project", nargs="?", default=str(WEB_ROOT.parent))
    voice_import = sub.add_parser("voice-import")
    voice_import.add_argument("audio")
    voice_import.add_argument("--phrase", type=int, required=True)
    voice_sync = sub.add_parser("voice-sync-status")
    voice_sync.add_argument("project", nargs="?", default=str(WEB_ROOT.parent))
    lipsync_ready = sub.add_parser("lipsync-readiness")
    lipsync_ready.add_argument("project", nargs="?", default=str(WEB_ROOT.parent))
    animatic_audit = sub.add_parser("animatic-audit")
    animatic_audit.add_argument("project", nargs="?", default=str(WEB_ROOT.parent))
    music = sub.add_parser("music-analysis")
    music.add_argument("project", nargs="?", default=str(WEB_ROOT.parent))
    font = sub.add_parser("font-check")
    font.add_argument("project", nargs="?", default=str(WEB_ROOT.parent))
    listen = sub.add_parser("listening-sync-status")
    listen.add_argument("project", nargs="?", default=str(WEB_ROOT.parent))
    rebuild_anim = sub.add_parser("rebuild-animatic")
    rebuild_anim.add_argument("project", nargs="?", default=str(WEB_ROOT.parent))
    rebuild_anim.add_argument("--version", default="")
    rebuild_anim.add_argument("--full-song", action="store_true")
    rebuild_anim.add_argument("--review-captions", action="store_true")
    rebuild_anim.add_argument("--brain-sync", action="store_true")
    rebuild_anim.add_argument("--sync-calibrated", action="store_true")
    cap_ready = sub.add_parser("caption-readiness")
    cap_ready.add_argument("project", nargs="?", default=str(WEB_ROOT.parent))
    diagnose = sub.add_parser("diagnose-route")
    diagnose.add_argument("route")
    auto_sync = sub.add_parser("auto-sync-lyrics")
    auto_sync.add_argument("project", nargs="?", default=str(WEB_ROOT.parent))
    auto_sync_stat = sub.add_parser("auto-sync-status")
    auto_sync_stat.add_argument("project", nargs="?", default=str(WEB_ROOT.parent))
    brain_sync = sub.add_parser("brain-sync")
    brain_sync.add_argument("project", nargs="?", default=str(WEB_ROOT.parent))
    brain_status = sub.add_parser("brain-sync-status")
    brain_status.add_argument("project", nargs="?", default=str(WEB_ROOT.parent))
    apply_offset = sub.add_parser("apply-caption-offset")
    apply_offset.add_argument("project", nargs="?", default=str(WEB_ROOT.parent))
    apply_offset.add_argument("--seconds", type=float, required=True)
    apply_offset.add_argument("--version", default="")
    music_brain = sub.add_parser("music-brain")
    music_brain.add_argument("project", nargs="?", default=str(WEB_ROOT.parent))
    sync_cal = sub.add_parser("sync-calibration-status")
    sync_cal.add_argument("project", nargs="?", default=str(WEB_ROOT.parent))
    suggest = sub.add_parser("suggest-caption-offset")
    suggest.add_argument("project", nargs="?", default=str(WEB_ROOT.parent))
    local_asr = sub.add_parser("local-asr-status")
    run_asr = sub.add_parser("run-local-asr")
    run_asr.add_argument("project", nargs="?", default=str(WEB_ROOT.parent))
    for name in [
        "audio-confidence-audit",
        "audio-align-v3",
        "audio-anchor-status",
        "audio-anchor-apply",
        "caption-audio-evaluate",
        "audio-truth-v3-status",
        "rebuild-audio-truth-v3",
        "rebuild-audio-truth-v4",
        "audio-truth-v4-status",
    ]:
        p = sub.add_parser(name)
        p.add_argument("project", nargs="?", default=str(WEB_ROOT.parent))

    for name, help_text in [
        ("sync-workspace", "Sync latest director plan into persistent storyboard/previs workspace"),
        ("build-animatic", "Build playable local animatic from storyboard cards"),
        ("review-status", "Print storyboard review counts"),
    ]:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("project", nargs="?", default=str(WEB_ROOT.parent))

    research = sub.add_parser("research")
    research.add_argument("project", nargs="?", default=str(WEB_ROOT.parent))
    research.add_argument("--query", default="mature side-travel performance references for a lonely blues-jazz bar music video")

    produce = sub.add_parser("produce")
    produce.add_argument("project", nargs="?", default=str(WEB_ROOT.parent))
    produce.add_argument("--dry-run", action="store_true")

    studio_create = sub.add_parser("studio-create")
    studio_create.add_argument("idea", nargs="?", default=DEFAULT_STUDIO_IDEA)
    studio_create.add_argument("--project", default=str(WEB_ROOT.parent))
    studio_continue = sub.add_parser("studio-continue")
    studio_continue.add_argument("project", nargs="?", default=str(WEB_ROOT.parent))
    studio_status = sub.add_parser("studio-status")
    studio_status.add_argument("project", nargs="?", default=str(WEB_ROOT.parent))
    studio_status.add_argument("--json", action="store_true")
    studio_watch = sub.add_parser("studio-watch")
    studio_watch.add_argument("loop_id", type=int)
    studio_eval = sub.add_parser("studio-evaluate")
    studio_eval.add_argument("loop_id", type=int)
    studio_repair = sub.add_parser("studio-repair")
    studio_repair.add_argument("loop_id", type=int)
    studio_resume = sub.add_parser("studio-resume")
    studio_resume.add_argument("loop_id", type=int)
    studio_cancel = sub.add_parser("studio-cancel")
    studio_cancel.add_argument("loop_id", type=int)
    studio_approve = sub.add_parser("studio-approve")
    studio_approve.add_argument("approval_id", type=int)
    studio_report_cmd = sub.add_parser("studio-report")
    studio_report_cmd.add_argument("loop_id", type=int)

    args = parser.parse_args()
    initialize_database()
    seed_from_existing_files()

    if args.command == "create":
        run_id = create_autonomous_run(args.idea, args.project)
        result = run_autonomous_studio(run_id, use_provider=True)
        print_run_status(result)
        return 0
    if args.command == "studio-create":
        loop_id = create_studio_loop(args.idea, args.project)
        result = run_studio_loop(loop_id)
        print(json.dumps({"loop_id": loop_id, "status": result["loop"]["status"], "score": result["loop"]["quality_score"], "next_action": result["loop"]["next_action"], "url": f"http://127.0.0.1:8787/studio-loop/{loop_id}"}, indent=2, ensure_ascii=False))
        return 0 if result["loop"]["status"] in {"acceptance_passed", "awaiting_approval", "stopped_with_blockers"} else 2
    if args.command == "studio-continue":
        result = continue_studio_loop(args.project)
        print(json.dumps({"loop_id": result["loop"]["loop_id"], "status": result["loop"]["status"], "score": result["loop"]["quality_score"], "next_action": result["loop"]["next_action"]}, indent=2, ensure_ascii=False))
        return 0
    if args.command == "studio-status":
        loop = latest_loop()
        if not loop:
            print(json.dumps({"status": "no_loop"}, indent=2))
            return 2
        detail = studio_loop_detail(int(loop["loop_id"]))
        if args.json:
            print(json.dumps(detail, indent=2, ensure_ascii=False))
        else:
            print(f"loop_id: {loop['loop_id']}")
            print(f"status: {loop['status']}")
            print(f"score: {loop['quality_score']}")
            print(f"iteration: {loop['current_iteration']}")
            print(f"next_action: {loop['next_action']}")
            print(f"url: http://127.0.0.1:8787/studio-loop/{loop['loop_id']}")
        return 0
    if args.command in {"studio-watch", "studio-evaluate"}:
        detail = studio_loop_detail(args.loop_id)
        key = "events" if args.command == "studio-watch" else "evaluation"
        print(json.dumps(detail.get(key, {}), indent=2, ensure_ascii=False))
        return 0
    if args.command in {"studio-repair", "studio-resume"}:
        result = run_studio_loop(args.loop_id)
        print(json.dumps({"loop_id": args.loop_id, "status": result["loop"]["status"], "score": result["loop"]["quality_score"], "next_action": result["loop"]["next_action"]}, indent=2, ensure_ascii=False))
        return 0
    if args.command == "studio-cancel":
        print(json.dumps(cancel_studio_loop(args.loop_id)["loop"], indent=2, ensure_ascii=False))
        return 5
    if args.command == "studio-approve":
        from app.studio_loop.orchestrator import approve_studio_loop

        print(json.dumps(approve_studio_loop(args.approval_id), indent=2, ensure_ascii=False))
        return 0
    if args.command == "studio-report":
        print(studio_loop_report(args.loop_id))
        return 0
    if args.command in {"continue", "analyze", "storyboard", "plan-production", "concepts"}:
        result = run_autonomous_director(DEFAULT_IDEA, args.project, dry_run=True)
        if args.command in {"storyboard", "plan-production"}:
            sync_workspace_from_latest_plan()
        print_status(result)
        return 0
    if args.command == "voice-test":
        print("voice_provider_status: planned_only; no API call; configure provider in /captions-voice")
        return 0
    if args.command == "provider-status":
        status = provider_capacity_status()
        if args.json:
            print(json.dumps(status, indent=2, ensure_ascii=False))
        else:
            print(f"active_provider: {status.get('active_provider')}")
            print(f"capacity: {status.get('capacity')}")
            print(f"known_warning: {status.get('known_warning')}")
        return 0
    if args.command == "resume-provider-run":
        result = resume_provider_run(args.run_id)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 6 if result["status"] == "awaiting_provider_capacity" else 0
    if args.command == "local-capabilities":
        result = local_capability_summary(refresh=True)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print("local_capabilities: audited")
            print(f"model_count: {result['models'].get('installed_model_count', 0)}")
            print(f"matrix_path: {WEB_ROOT.parent / 'director-os/state/LOCAL_CAPABILITY_MATRIX.json'}")
        return 0
    if args.command == "motion-analyze":
        print({"video_path": args.video_path, "status": "metadata_analysis_requires_registered_motion_reference"})
        return 0
    if args.command == "lipsync-plan":
        print(json.dumps(build_lipsync_plan(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "lipsync-status":
        print(json.dumps({"jobs": list_lipsync_jobs()}, indent=2, ensure_ascii=False))
        return 0
    if args.command == "lipsync-export":
        job_id = create_lipsync_job(args.shot_id)
        ok, message, path = create_manual_infinitetalk_export(job_id)
        print(json.dumps({"ok": ok, "message": message, "job_id": job_id, "path": path}, indent=2))
        return 0 if ok else 2
    if args.command == "lipsync-import":
        print(json.dumps({"status": "planned", "result_path": args.result_path, "shot": args.shot, "note": "Use result import/QC route for managed media intake."}, indent=2))
        return 0
    if args.command == "lipsync-qc":
        print(json.dumps({"status": "manual_review_required", "result_id": args.result_id}, indent=2))
        return 0
    if args.command == "lipsync-submit-runpod":
        print("refused: exact-upload approval, privacy approval, spend approval and endpoint configuration are required")
        return 2
    if args.command == "burmese-converter-status":
        print(json.dumps(converter_status(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "burmese-conversion-review-status":
        print(json.dumps(conversion_review_summary(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "burmese-convert":
        path = Path(args.file)
        text = path.read_text(encoding="utf-8")
        lines = [zawgyi_to_unicode(line, confidence=1.0) for line in text.splitlines()]
        if args.preview:
            print(json.dumps(lines, indent=2, ensure_ascii=False))
        return 0
    if args.command == "rebuild-captions":
        if args.version == "v6" and getattr(args, "sync_calibrated", False):
            print(json.dumps(rebuild_caption_v6(), indent=2, ensure_ascii=False))
            return 0
        if args.version == "v5" and getattr(args, "brain_sync", False):
            print(json.dumps(rebuild_caption_v5(), indent=2, ensure_ascii=False))
            return 0
        if args.version == "v4" and args.auto_sync:
            print(json.dumps(rebuild_caption_v4(), indent=2, ensure_ascii=False))
            return 0
        if args.version != "v2":
            print("supported caption rebuilds: --version v2, --version v4 --auto-sync, --version v5 --brain-sync, or --version v6 --sync-calibrated")
            return 2
        print(json.dumps(rebuild_caption_v2(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "lyric-alignment-status":
        print(json.dumps(validate_phrase_timing(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "voice-import":
        ok, message, payload = import_voice_audio_for_phrase(args.phrase, args.audio)
        print(json.dumps({"ok": ok, "message": message, "payload": payload}, indent=2, ensure_ascii=False))
        return 0 if ok else 2
    if args.command == "voice-sync-status":
        print(json.dumps(voice_sync_summary(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "lipsync-readiness":
        v4_status_path = WEB_ROOT.parent / "director-os/projects/burmese-music-video/audio-truth/v4/AUDIO_TRUTH_V4_STATUS.json"
        if v4_status_path.exists():
            status = json.loads(v4_status_path.read_text(encoding="utf-8"))
            lipsync = status.get("lipsync") or {}
            print(json.dumps({
                "source": "AUDIO_TRUTH_TIMELINE_V4",
                "status": "replacement_anchor_review_required",
                "ready_occurrence_count": lipsync.get("ready_occurrence_count", 0),
                "blocked_occurrence_count": lipsync.get("blocked_occurrence_count", 0),
                "blocked": lipsync.get("blocked", []),
                "latest_preview_url": "http://127.0.0.1:8787/studio-assets/burmese-music-video/previews/audio-truth-v4/CREATIVE_SKETCH_AUDIO_TRUTH_V4_WITH_CAPTIONS.mp4",
                "next_action": status.get("next_action"),
            }, indent=2, ensure_ascii=False))
            return 0
        v3_status_path = WEB_ROOT.parent / "director-os/projects/burmese-music-video/audio-truth/v3/AUDIO_TRUTH_V3_STATUS.json"
        if v3_status_path.exists():
            status = json.loads(v3_status_path.read_text(encoding="utf-8"))
            lipsync = status.get("lipsync") or {}
            print(json.dumps({
                "source": "AUDIO_TRUTH_TIMELINE_V3",
                "status": "ready_with_anchor_review" if lipsync.get("ready_occurrence_count", 0) else "blocked",
                "ready_occurrence_count": lipsync.get("ready_occurrence_count", 0),
                "blocked_occurrence_count": lipsync.get("blocked_occurrence_count", 0),
                "blockers": lipsync.get("blockers", []),
                "requirements": [
                    "resolved occurrence mapping",
                    "caption timing and master-audio timing share the same timebase",
                    "no lyric mismatch",
                    "not instrumental",
                    "sufficient alignment confidence or explicit anchor/user approval",
                    "segment validates with ffprobe",
                ],
                "latest_preview_url": "http://127.0.0.1:8787/studio-assets/burmese-music-video/previews/audio-truth-v3/CREATIVE_SKETCH_AUDIO_TRUTH_V3_WITH_CAPTIONS.mp4",
                "next_action": status.get("next_action"),
            }, indent=2, ensure_ascii=False))
            return 0
        print(json.dumps(brain_lipsync_readiness(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "diagnose-route":
        if args.route != "/animatic":
            print(json.dumps({"route": args.route, "status": "not_implemented_for_cli_diagnosis"}, indent=2))
            return 2
        print(json.dumps(diagnose_animatic_route(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "auto-sync-lyrics":
        print(json.dumps(auto_sync_lyrics(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "auto-sync-status":
        data = auto_sync_status()
        print(json.dumps({k: data[k] for k in ["status", "method", "auto_synced_phrase_count", "low_confidence_phrase_count", "blocked_phrase_count", "warning"]}, indent=2, ensure_ascii=False))
        return 0
    if args.command == "brain-sync":
        print(json.dumps(build_brain_timeline(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "brain-sync-status":
        data = brain_timeline_status()
        print(json.dumps({
            "version": data["version"],
            "master_duration": data["master_duration"],
            "sync_method_counts": data["sync_method_counts"],
            "global_offset": data["offset"]["global_caption_delay_seconds"],
            "captions_ahead_or_late": "captions_ahead_corrected" if data["offset"]["global_caption_delay_seconds"] > 0 else "no_global_offset",
            "high_confidence_phrase_count": data["high_confidence_phrase_count"],
            "low_confidence_phrase_count": data["low_confidence_phrase_count"],
            "blocked_phrase_count": data["blocked_phrase_count"],
            "latest_brain_sync_animatic_url": "http://127.0.0.1:8787/director-assets/animatics/14/ANIMATIC_WITH_CAPTIONS_BRAIN_SYNC_REVIEW.mp4",
        }, indent=2, ensure_ascii=False))
        return 0
    if args.command == "apply-caption-offset":
        if getattr(args, "version", "") == "v6":
            print(json.dumps(approve_global_caption_offset(args.seconds), indent=2, ensure_ascii=False))
        else:
            print(json.dumps(apply_caption_offset(args.seconds), indent=2, ensure_ascii=False))
        return 0
    if args.command == "music-brain":
        data = brain_timeline_status()
        print(json.dumps({"path": str(WEB_ROOT.parent / "director-os/state/PRODUCTION_BRAIN_TIMELINE.json"), "phrases": len(data["events"]), "offset": data["offset"]["global_caption_delay_seconds"], "low_confidence": data["low_confidence_phrase_count"]}, indent=2, ensure_ascii=False))
        return 0
    if args.command == "sync-calibration-status":
        print(json.dumps(sync_calibration_status(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "suggest-caption-offset":
        print(json.dumps(generate_offset_candidates(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "local-asr-status":
        print(json.dumps(asr_health(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "run-local-asr":
        print(json.dumps(run_local_asr_alignment(), indent=2, ensure_ascii=False))
        return 0
    if args.command in {"audio-align-v3", "rebuild-audio-truth-v3"}:
        print(json.dumps(run_audio_truth_v24(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "rebuild-audio-truth-v4":
        print(json.dumps(run_audio_truth_v241(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "audio-confidence-audit":
        print(json.dumps(read_state_json("AUDIO_TRUTH_CONFIDENCE_AUDIT.json"), indent=2, ensure_ascii=False))
        return 0
    if args.command == "audio-anchor-status":
        print(json.dumps(read_state_json("AUDIO_TRUTH_ANCHORS.json"), indent=2, ensure_ascii=False))
        return 0
    if args.command == "audio-anchor-apply":
        payload = read_state_json("AUDIO_TRUTH_ANCHOR_FEEDBACK.json")
        if not payload:
            payload = {"status": "pending", "anchors_confirmed": 0}
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    if args.command == "caption-audio-evaluate":
        path = WEB_ROOT.parent / "director-os/projects/burmese-music-video/audio-truth/v3/evaluation/CAPTION_VOCAL_TIMING.json"
        print(json.dumps(json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}, indent=2, ensure_ascii=False))
        return 0
    if args.command == "audio-truth-v3-status":
        path = WEB_ROOT.parent / "director-os/projects/burmese-music-video/audio-truth/v3/AUDIO_TRUTH_V3_STATUS.json"
        status = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        print(json.dumps({
            "reason_v2_zero_high": status.get("v2_zero_high_confidence_cause"),
            "tokenizer": status.get("tokenizer"),
            "selected_stem": status.get("selected_stem"),
            "full_song_path": status.get("full_song_path"),
            "confidence_counts": status.get("timeline"),
            "anchor_status": status.get("anchors"),
            "caption_defects": status.get("evaluation"),
            "production_caption_ready": (status.get("captions") or {}).get("production_ready"),
            "lipsync_ready_count": (status.get("lipsync") or {}).get("ready_occurrence_count"),
            "latest_preview_url": "http://127.0.0.1:8787/studio-assets/burmese-music-video/previews/audio-truth-v3/CREATIVE_SKETCH_AUDIO_TRUTH_V3_WITH_CAPTIONS.mp4",
            "next_action": status.get("next_action"),
        }, indent=2, ensure_ascii=False))
        return 0
    if args.command == "audio-truth-v4-status":
        path = WEB_ROOT.parent / "director-os/projects/burmese-music-video/audio-truth/v4/AUDIO_TRUTH_V4_STATUS.json"
        status = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        print(json.dumps({
            "invalidated_v3_anchor_set": status.get("invalidated_v3_anchor_set"),
            "first_anchor": status.get("first_anchor"),
            "anchors": status.get("anchors"),
            "timeline": status.get("timeline"),
            "caption_audio_validation": status.get("caption_audio_validation"),
            "playback_validation": status.get("playback_validation"),
            "production_caption_ready": (status.get("captions") or {}).get("production_ready"),
            "lipsync_ready_count": (status.get("lipsync") or {}).get("ready_occurrence_count"),
            "latest_preview_url": "http://127.0.0.1:8787/studio-assets/burmese-music-video/previews/audio-truth-v4/CREATIVE_SKETCH_AUDIO_TRUTH_V4_WITH_CAPTIONS.mp4",
            "next_action": status.get("next_action"),
        }, indent=2, ensure_ascii=False))
        return 0
    if args.command == "animatic-audit":
        print(json.dumps(animatic_reality_audit(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "music-analysis":
        data = music_analysis()
        print(json.dumps({"duration": data["duration"], "vocal_phrases": len(data["vocal_phrase_regions"]), "instrumental_regions": len(data["instrumental_regions"]), "path": str(WEB_ROOT.parent / "director-os/state/MUSIC_ANALYSIS.json")}, indent=2))
        return 0
    if args.command == "font-check":
        print(json.dumps(font_render_preview(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "listening-sync-status":
        data = listening_sync_status()
        print(json.dumps({k: data[k] for k in ["status", "verified_phrases", "unverified_phrases", "wrong_line_phrases", "review_url"]}, indent=2, ensure_ascii=False))
        return 0
    if args.command == "rebuild-animatic":
        if args.version == "15" and getattr(args, "sync_calibrated", False):
            print(json.dumps(build_animatic_v15(), indent=2, ensure_ascii=False))
            return 0
        if args.version == "14" and getattr(args, "brain_sync", False):
            print(json.dumps(build_animatic_v14(), indent=2, ensure_ascii=False))
            return 0
        if not args.full_song:
            print("refused: rebuild requires --full-song")
            return 2
        if args.version and args.version != "13":
            print("refused: v1.0.5 supports explicit --version 13 for this repair")
            return 2
        print(json.dumps(build_animatic_v13(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "caption-readiness":
        print(json.dumps(v105_caption_readiness(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "research":
        write_research_audit()
        print(research_search_assistant(args.query))
        return 0
    if args.command == "produce":
        result = run_autonomous_director(DEFAULT_IDEA, args.project, dry_run=True)
        print("dry_run_only: true")
        print_status(result)
        return 0
    if args.command == "status":
        runs = list_runs()
        if runs:
            result = run_status(runs[0]["run_id"])
            if getattr(args, "json", False):
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print_run_status(result)
            return status_exit_code(result)
        else:
            result = director_status()
            if getattr(args, "json", False):
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print_status(result)
        return 0
    if args.command == "sync-workspace":
        print(sync_workspace_from_latest_plan())
        return 0
    if args.command == "build-animatic":
        runs = list_runs()
        if runs:
            print(build_edit_handoff(int(runs[0]["run_id"])))
        else:
            print(build_animatic())
        return 0
    if args.command == "review-status":
        print(workspace_summary())
        return 0
    return 2


def print_status(result: dict) -> None:
    state = result.get("state") or {}
    print(f"has_plan: {result.get('has_plan')}")
    print(f"plan_path: {result.get('plan_path')}")
    print(f"storyboard_path: {result.get('storyboard_path')}")
    print(f"storyboard_count: {state.get('storyboard_count', 0)}")
    print(f"shot_count: {state.get('shot_count', 0)}")
    print(f"next_best_action: {result.get('next_best_action')}")


def print_run_status(result: dict) -> None:
    run = result.get("run") or {}
    groups = result.get("blocker_groups") or {}
    print(f"run_id: {run.get('run_id')}")
    print(f"status: {run.get('status')}")
    print(f"current_stage: {run.get('current_stage')}")
    print(f"completed_stages: {result.get('completed_stages')}/{result.get('total_stages')}")
    print(f"last_artifact: {result.get('last_artifact')}")
    print("hard_blockers:")
    print_group(groups.get("hard_blockers", []))
    print("required_inputs:")
    print_group(groups.get("required_inputs", []))
    print("approvals_needed:")
    print_group(groups.get("approvals_needed", []))
    print("optional_capabilities:")
    print_group(groups.get("optional_capabilities", []))
    print("warnings:")
    print_group(groups.get("warnings", []))
    print("created:")
    for item in ["director treatment", "24-shot storyboard", "24 visual grammar records", "24 blocking diagrams", "MP4 animatic", "caption exports", "renderer strategy"]:
        print(f"- {item}")
    print(f"next_action: {result.get('next_action')}")
    print(f"web_url: {result.get('web_url')}")


def print_group(items: list[dict]) -> None:
    if not items:
        print("- none")
        return
    for item in items:
        print(f"- {item.get('code')}")


def status_exit_code(result: dict) -> int:
    status = (result.get("run") or {}).get("status")
    groups = result.get("blocker_groups") or {}
    if status in {"ready", "ready_with_approvals"}:
        return 0
    if status == "awaiting_required_input":
        return 2
    if groups.get("hard_blockers"):
        return 3
    if status == "failed":
        return 4
    if status == "cancelled":
        return 5
    return 0


def read_state_json(name: str) -> dict:
    path = WEB_ROOT.parent / "director-os" / "state" / name
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
