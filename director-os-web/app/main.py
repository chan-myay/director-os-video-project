from __future__ import annotations

from urllib.parse import parse_qsl, quote
from pathlib import Path
import re

from fastapi import FastAPI, Request
from app.creator_server import creator_app
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import APP_NAME, APP_ROOT, APP_VERSION, RESULT_MEDIA_ROOT
from app.services.connector_service import connector_status
from app.services.approval_service import create_approval, list_approvals
from app.services.audit_service import list_audit_logs
from app.services.autonomous_director_service import (
    DEFAULT_IDEA,
    director_status,
    research_search_assistant,
    run_autonomous_director,
    write_research_audit,
)
from app.services.db import initialize_database
from app.services.director_workspace_service import (
    add_research_items,
    analyze_motion_reference,
    build_animatic,
    comment_storyboard_card,
    create_voice_test,
    decide_storyboard_card,
    list_caption_lines,
    list_motion_analyses,
    list_research_items,
    list_storyboard_cards,
    list_voice_tests,
    sync_workspace_from_latest_plan,
    update_caption_line,
    workspace_summary,
)
from app.services.engine_reader import engine_status
from app.services.generated_request_service import get_generated_file, list_generated_requests
from app.services.job_service import (
    create_job,
    generated_request_options,
    get_job,
    job_readiness,
    list_jobs,
    run_job_dry_run,
)
from app.services.manual_export_service import (
    correct_existing_export_three,
    create_manual_export,
    get_manual_export,
    list_manual_exports,
)
from app.burmese.zawgyi_unicode_service import converter_status
from app.services.burmese_language_service import build_burmese_timeline, burmese_language_summary
from app.services.lyric_timing_service import (
    approve_all_high_confidence_validated,
    conversion_review_summary,
    import_voice_audio_for_phrase,
    lyric_timing_summary,
    rebuild_caption_v2,
    update_conversion_review,
    validate_phrase_timing,
    voice_sync_summary,
)
from app.services.lipsync_service import (
    build_lipsync_plan,
    classify_lipsync_shots,
    create_lipsync_job,
    create_manual_infinitetalk_export,
    get_lipsync_job,
    lipsync_dashboard,
    lipsync_outputs_for_job,
    list_lipsync_jobs,
    refresh_lipsync_provider_health,
)
from app.services.local_capability_service import local_capability_summary, run_local_capability_audit
from app.services.moodboard_service import create_moodboard, list_moodboards
from app.services.motion_reference_service import create_motion_reference, get_latest_motion_reference, list_motion_references
from app.services.product_status_service import product_documents, product_status
from app.services.qc_service import create_qc_review, list_qc_reviews
from app.services.reference_service import reference_status
from app.services.result_decision_service import submit_result_decision
from app.services.result_import_service import get_result, import_result_from_path, list_results, result_counts
from app.services.result_qc_service import submit_result_review
from app.services.shot_pack_service import get_shot_pack, list_shot_packs
from app.services.v09_studio_service import (
    build_edit_handoff,
    create_autonomous_run,
    list_runs,
    retry_stage,
    run_autonomous_studio,
    run_status,
    set_run_status,
)
from app.services.v104_animatic_sync_service import (
    animatic_reality_audit,
    font_check,
    listening_sync_status,
    music_analysis,
    update_listening_sync,
)
from app.audio.auto_sync_service import (
    auto_sync_lyrics,
    auto_sync_status,
    build_animatic_v13,
    font_render_preview,
    rebuild_caption_v4,
    v105_caption_readiness,
    v105_lipsync_readiness,
)
from app.audio.brain_sync_service import (
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
from app.audio.sync_offset_service import generate_offset_candidates, sync_calibration_status
from app.audio.asr.asr_health import asr_health
from app.audio_truth.orchestrator import audio_truth_status, run_audio_truth_engine, run_audio_truth_v23, run_audio_truth_v24, run_audio_truth_v241, studio_audio_truth_context
from app.services.latest_safe_animatic_service import latest_safe_animatic_context, resolve_director_asset
from app.services.setup_decision_service import (
    burmese_voice_decision_context,
    list_setup_decisions,
    record_setup_decision,
    system_tools_context,
)
from app.services.studio_service import (
    DEFAULT_PROJECT_ID,
    continue_and_improve,
    create_everything,
    create_project,
    ingest_uploads,
    project_context,
    studio_asset,
    studio_home_context,
)
from app.services.storyboard_model_service import (
    generate_storyboard_ai_variant,
    list_storyboard_variants,
    record_storyboard_model_decision,
    storyboard_model_decision_context,
)
from app.services.workflow_service import connector_records, seed_from_existing_files, workflow_summary
from app.intelligence.provider_health import provider_status
from app.studio_loop.orchestrator import (
    DEFAULT_STUDIO_IDEA,
    cancel_studio_loop,
    create_studio_loop,
    latest_loop,
    list_studio_loops,
    run_studio_loop,
    studio_loop_detail,
)
from app.studio_loop.event_stream import sse_events
from app.services.rescue_studio_service import (
    PROJECT_ROOT as RESCUE_PROJECT_ROOT,
    RESCUE_ROOT,
    apply_refinement,
    build_rescue_artifacts,
    import_generated_files,
    reorder_shots,
    rescue_context,
    set_shot_state,
    start_background_rebuild,
)


app = FastAPI(title=APP_NAME, version=APP_VERSION)
app.mount("/creator", creator_app)
app.mount("/static", StaticFiles(directory=APP_ROOT / "app" / "static"), name="static")
RESCUE_ROOT.mkdir(parents=True, exist_ok=True)
app.mount("/rescue-assets", StaticFiles(directory=RESCUE_ROOT), name="rescue-assets")
app.mount("/source-assets", StaticFiles(directory=APP_ROOT.parent / "director-os"), name="source-assets")
app.mount("/reference-assets", StaticFiles(directory=APP_ROOT.parent / "references"), name="reference-assets")
app.mount("/project-source", StaticFiles(directory=APP_ROOT.parent), name="project-source")
templates = Jinja2Templates(directory=APP_ROOT / "app" / "templates")


@app.on_event("startup")
def startup() -> None:
    initialize_database()
    seed_from_existing_files()
    correct_existing_export_three()


def context(request: Request, **extra: object) -> dict[str, object]:
    base = {"request": request, "app_name": APP_NAME, "app_version": APP_VERSION}
    base.update(extra)
    return base


async def form_dict(request: Request) -> dict[str, str]:
    body = (await request.body()).decode("utf-8")
    return {key: value for key, value in parse_qsl(body, keep_blank_values=True)}


class MemoryUpload:
    def __init__(self, filename: str, content: bytes) -> None:
        self.filename = filename
        self._content = content
        self._offset = 0

    async def read(self, size: int = -1) -> bytes:
        if self._offset >= len(self._content):
            return b""
        if size is None or size < 0:
            size = len(self._content) - self._offset
        chunk = self._content[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk


async def multipart_files(request: Request) -> list[MemoryUpload]:
    content_type = request.headers.get("content-type", "")
    match = re.search(r"boundary=([^;]+)", content_type)
    if not match:
        return []
    boundary = match.group(1).strip('"').encode("utf-8")
    body = await request.body()
    files: list[MemoryUpload] = []
    for part in body.split(b"--" + boundary):
        part = part.strip()
        if not part or part == b"--" or b"\r\n\r\n" not in part:
            continue
        headers_blob, content = part.split(b"\r\n\r\n", 1)
        if content.endswith(b"\r\n"):
            content = content[:-2]
        if content.endswith(b"--"):
            content = content[:-2]
        headers = headers_blob.decode("utf-8", errors="ignore")
        filename_match = re.search(r'filename="([^"]*)"', headers)
        if filename_match and filename_match.group(1):
            files.append(MemoryUpload(filename_match.group(1), content))
    return files


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse("/create", status_code=307)


@app.get("/create", response_class=HTMLResponse)
def rescue_create(request: Request) -> HTMLResponse:
    response = templates.TemplateResponse("rescue_create.html", context(request, **rescue_context()))
    response.headers["Cache-Control"] = "no-store"
    return response


@app.post("/create/build")
async def rescue_build(request: Request) -> dict:
    form = await form_dict(request)
    started = start_background_rebuild(form.get("idea", "") or "Building storyboard and video sketch")
    return {"accepted": True, "started": started, "result_url": "/create#results"}


@app.get("/create/status")
def rescue_status() -> dict:
    return rescue_context()["job"]


@app.post("/create/refine")
async def rescue_refine(request: Request) -> dict:
    form = await form_dict(request)
    return apply_refinement(form.get("refinement", ""))


@app.post("/create/import")
async def rescue_import(request: Request) -> dict:
    files = await multipart_files(request)
    return import_generated_files(files)


@app.post("/create/shot/{shot_number}/enabled")
async def rescue_shot_enabled(request: Request, shot_number: int) -> dict:
    form = await form_dict(request)
    shot = set_shot_state(shot_number, form.get("enabled", "true").lower() == "true")
    return {"accepted": bool(shot), "shot": shot}


@app.post("/create/reorder")
async def rescue_reorder(request: Request) -> dict:
    form = await form_dict(request)
    order = [int(value) for value in form.get("order", "").split(",") if value.strip().isdigit()]
    reorder_shots(order)
    return {"accepted": True, "order": order}


@app.post("/create/rebuild")
def rescue_rebuild() -> dict:
    return {"accepted": True, "started": start_background_rebuild("Rebuilding full storyboard animation")}


@app.get("/command-center", response_class=HTMLResponse)
def command_center(request: Request, message: str = "") -> HTMLResponse:
    return templates.TemplateResponse(
        "command_center.html",
        context(
            request,
            default_idea=DEFAULT_IDEA,
            studio_idea=DEFAULT_STUDIO_IDEA,
            status=director_status(),
            latest_studio_loop=latest_loop(),
            safe=latest_safe_animatic_context(),
            message=message,
        ),
    )


@app.get("/studio", response_class=HTMLResponse)
def studio_home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("studio.html", context(request, audio_truth=audio_truth_status(), **studio_home_context()))


@app.post("/studio/projects/new", response_class=HTMLResponse)
async def studio_project_new(request: Request) -> RedirectResponse:
    form = await form_dict(request)
    project = create_project(form.get("name", "Untitled Studio Project"))
    return RedirectResponse(f"/studio/projects/{project['project_id']}", status_code=303)


@app.get("/studio/projects/{project_id}", response_class=HTMLResponse)
def studio_project(request: Request, project_id: str) -> HTMLResponse:
    return templates.TemplateResponse("studio_project.html", context(request, audio_truth=audio_truth_status(), **project_context(project_id)))


@app.post("/studio/projects/{project_id}/upload", response_class=HTMLResponse)
async def studio_project_upload(request: Request, project_id: str) -> RedirectResponse:
    files = await multipart_files(request)
    await ingest_uploads(project_id, files)
    return RedirectResponse(f"/studio/projects/{project_id}", status_code=303)


@app.post("/studio/projects/{project_id}/create", response_class=HTMLResponse)
async def studio_project_create(request: Request, project_id: str) -> RedirectResponse:
    form = await form_dict(request)
    idea = form.get("idea", DEFAULT_STUDIO_IDEA)
    create_everything(project_id, idea)
    return RedirectResponse(f"/studio/projects/{project_id}/result", status_code=303)


@app.post("/studio/projects/{project_id}/continue", response_class=HTMLResponse)
async def studio_project_continue(request: Request, project_id: str) -> RedirectResponse:
    form = await form_dict(request)
    continue_and_improve(project_id, form.get("refinement", ""))
    return RedirectResponse(f"/studio/projects/{project_id}/result", status_code=303)


@app.get("/studio/projects/{project_id}/progress", response_class=HTMLResponse)
def studio_project_progress(request: Request, project_id: str) -> HTMLResponse:
    return templates.TemplateResponse("studio_progress.html", context(request, **project_context(project_id)))


@app.get("/studio/projects/{project_id}/result", response_class=HTMLResponse)
def studio_project_result(request: Request, project_id: str) -> HTMLResponse:
    return templates.TemplateResponse("studio_result.html", context(request, audio_truth=audio_truth_status(), **project_context(project_id)))


@app.get("/studio/projects/{project_id}/storyboard", response_class=HTMLResponse)
def studio_project_storyboard(request: Request, project_id: str) -> HTMLResponse:
    return templates.TemplateResponse("studio_storyboard.html", context(request, **project_context(project_id)))


@app.get("/studio/projects/{project_id}/audio-truth", response_class=HTMLResponse)
def studio_project_audio_truth(request: Request, project_id: str) -> RedirectResponse:
    return RedirectResponse("/advanced/audio-truth", status_code=307)


@app.get("/advanced/audio-truth", response_class=HTMLResponse)
def advanced_audio_truth(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "advanced_audio_archive.html",
        context(request),
    )


@app.post("/studio/projects/{project_id}/audio-truth/run", response_class=HTMLResponse)
def studio_project_audio_truth_run(request: Request, project_id: str) -> RedirectResponse:
    return RedirectResponse("/advanced/audio-truth", status_code=303)


@app.post("/studio/projects/{project_id}/audio-truth/run-v23", response_class=HTMLResponse)
def studio_project_audio_truth_run_v23(request: Request, project_id: str) -> RedirectResponse:
    return RedirectResponse("/advanced/audio-truth", status_code=303)


@app.post("/studio/projects/{project_id}/audio-truth/run-v24", response_class=HTMLResponse)
def studio_project_audio_truth_run_v24(request: Request, project_id: str) -> RedirectResponse:
    return RedirectResponse("/advanced/audio-truth", status_code=303)


@app.post("/studio/projects/{project_id}/audio-truth/run-v241", response_class=HTMLResponse)
def studio_project_audio_truth_run_v241(request: Request, project_id: str) -> RedirectResponse:
    return RedirectResponse("/advanced/audio-truth", status_code=303)


@app.get("/studio-assets/{project_id}/{asset_path:path}")
def studio_assets(request: Request, project_id: str, asset_path: str) -> Response:
    path, status, message = studio_asset(project_id, asset_path)
    if path and status == 200:
        range_header = request.headers.get("range", "")
        if path.suffix.lower() == ".mp4" and range_header.startswith("bytes="):
            file_size = path.stat().st_size
            range_value = range_header[len("bytes="):].split(",", 1)[0]
            start_text, _, end_text = range_value.partition("-")
            try:
                start = int(start_text) if start_text else 0
                end = int(end_text) if end_text else min(start + 1024 * 1024 - 1, file_size - 1)
            except ValueError:
                return Response(status_code=416, headers={"Content-Range": f"bytes */{file_size}"})
            start = max(0, min(start, file_size - 1))
            end = max(start, min(end, file_size - 1))

            def iter_file() -> bytes:
                with path.open("rb") as handle:
                    handle.seek(start)
                    remaining = end - start + 1
                    while remaining > 0:
                        chunk = handle.read(min(64 * 1024, remaining))
                        if not chunk:
                            break
                        remaining -= len(chunk)
                        yield chunk

            return StreamingResponse(
                iter_file(),
                status_code=206,
                media_type="video/mp4",
                headers={
                    "Accept-Ranges": "bytes",
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                    "Content-Length": str(end - start + 1),
                },
            )
        return FileResponse(path)
    return HTMLResponse(
        f"<html><body><h1>Studio asset unavailable</h1><p>{message}</p><p><code>{project_id}/{asset_path}</code></p></body></html>",
        status_code=status,
    )


@app.post("/studio-loop/create", response_class=HTMLResponse)
async def studio_loop_create(request: Request) -> RedirectResponse:
    form = await form_dict(request)
    idea = form.get("idea", DEFAULT_STUDIO_IDEA)
    project_path = form.get("project_path", str(APP_ROOT.parent))
    loop_id = create_studio_loop(idea, project_path)
    run_studio_loop(loop_id)
    return RedirectResponse(f"/studio-loop/{loop_id}", status_code=303)


@app.get("/studio-loop", response_class=HTMLResponse)
def studio_loop_index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("studio_loop_index.html", context(request, loops=list_studio_loops(), default_idea=DEFAULT_STUDIO_IDEA))


@app.get("/studio-loop/{loop_id:int}", response_class=HTMLResponse)
def studio_loop_show(request: Request, loop_id: int) -> HTMLResponse:
    return templates.TemplateResponse("studio_loop_detail.html", context(request, detail=studio_loop_detail(loop_id)))


@app.get("/studio-loop/{loop_id:int}/live")
def studio_loop_live(loop_id: int) -> StreamingResponse:
    detail = studio_loop_detail(loop_id)
    return StreamingResponse(sse_events(detail.get("events", [])), media_type="text/event-stream")


@app.get("/studio-loop/{loop_id:int}/artifacts", response_class=HTMLResponse)
def studio_loop_artifacts(request: Request, loop_id: int) -> HTMLResponse:
    return templates.TemplateResponse("studio_loop_artifacts.html", context(request, detail=studio_loop_detail(loop_id)))


@app.get("/studio-loop/{loop_id:int}/evaluation", response_class=HTMLResponse)
def studio_loop_evaluation(request: Request, loop_id: int) -> HTMLResponse:
    return templates.TemplateResponse("studio_loop_evaluation.html", context(request, detail=studio_loop_detail(loop_id)))


@app.get("/studio-loop/{loop_id:int}/repairs", response_class=HTMLResponse)
def studio_loop_repairs(request: Request, loop_id: int) -> HTMLResponse:
    return templates.TemplateResponse("studio_loop_repairs.html", context(request, detail=studio_loop_detail(loop_id)))


@app.get("/studio-loop/{loop_id:int}/approvals", response_class=HTMLResponse)
def studio_loop_approvals(request: Request, loop_id: int) -> HTMLResponse:
    return templates.TemplateResponse("studio_loop_approvals.html", context(request, detail=studio_loop_detail(loop_id)))


@app.post("/studio-loop/{loop_id:int}/continue", response_class=HTMLResponse)
def studio_loop_continue(request: Request, loop_id: int) -> RedirectResponse:
    run_studio_loop(loop_id)
    return RedirectResponse(f"/studio-loop/{loop_id}", status_code=303)


@app.post("/studio-loop/{loop_id:int}/cancel", response_class=HTMLResponse)
def studio_loop_cancel(request: Request, loop_id: int) -> RedirectResponse:
    cancel_studio_loop(loop_id)
    return RedirectResponse(f"/studio-loop/{loop_id}", status_code=303)


@app.post("/director-plan/create", response_class=HTMLResponse)
async def director_plan_create(request: Request) -> RedirectResponse:
    form = await form_dict(request)
    run_autonomous_director(form.get("idea", DEFAULT_IDEA), form.get("project_path", str(APP_ROOT.parent)), dry_run=True)
    return RedirectResponse("/director-plan?message=created", status_code=303)


@app.get("/director-plan", response_class=HTMLResponse)
def director_plan(request: Request, message: str = "") -> HTMLResponse:
    return templates.TemplateResponse("director_plan.html", context(request, status=director_status(), message=message))


@app.get("/settings/intelligence", response_class=HTMLResponse)
def intelligence_settings(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("intelligence_settings.html", context(request, provider=provider_status()))


@app.get("/settings/system-tools", response_class=HTMLResponse)
def system_tools_settings(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("system_tools.html", context(request, tools=system_tools_context()))


@app.get("/settings/local-capabilities", response_class=HTMLResponse)
def local_capabilities_settings(request: Request, refresh: str = "") -> HTMLResponse:
    data = local_capability_summary(refresh == "1")
    return templates.TemplateResponse("local_capabilities.html", context(request, capabilities=data))


@app.post("/settings/local-capabilities/refresh", response_class=HTMLResponse)
def local_capabilities_refresh(request: Request) -> RedirectResponse:
    run_local_capability_audit()
    return RedirectResponse("/settings/local-capabilities", status_code=303)


@app.get("/setup/storyboard-model", response_class=HTMLResponse)
def setup_storyboard_model(request: Request, message: str = "") -> HTMLResponse:
    return templates.TemplateResponse(
        "setup_storyboard_model.html",
        context(request, setup=storyboard_model_decision_context(), decisions=list_setup_decisions(), message=message),
    )


@app.post("/setup/storyboard-model", response_class=HTMLResponse)
async def setup_storyboard_model_save(request: Request) -> RedirectResponse:
    form = await form_dict(request)
    result = record_storyboard_model_decision(form.get("choice", "decide_later"), form.get("notes", ""))
    suffix = "approval recorded; no download executed" if result.get("installer_package") else "decision recorded"
    return RedirectResponse(f"/setup/storyboard-model?message={quote(suffix)}", status_code=303)


@app.get("/setup/burmese-voice", response_class=HTMLResponse)
def setup_burmese_voice(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "setup_burmese_voice.html",
        context(request, setup=burmese_voice_decision_context(), decisions=list_setup_decisions()),
    )


@app.post("/setup/burmese-voice", response_class=HTMLResponse)
async def setup_burmese_voice_save(request: Request) -> RedirectResponse:
    form = await form_dict(request)
    record_setup_decision("burmese_voice", form.get("choice", "caption_only"), form.get("notes", ""))
    return RedirectResponse("/setup/burmese-voice", status_code=303)


@app.get("/director-runs", response_class=HTMLResponse)
def director_runs(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("director_runs.html", context(request, runs=list_runs()))


@app.get("/director-runs/new", response_class=HTMLResponse)
def director_runs_new(request: Request, message: str = "") -> HTMLResponse:
    return templates.TemplateResponse(
        "director_run_new.html",
        context(request, default_idea=DEFAULT_IDEA, message=message, provider=provider_status()),
    )


@app.post("/director-runs/new", response_class=HTMLResponse)
async def director_runs_create(request: Request) -> RedirectResponse:
    form = await form_dict(request)
    run_id = create_autonomous_run(form.get("idea", DEFAULT_IDEA), form.get("project_path", str(APP_ROOT.parent)))
    return RedirectResponse(f"/director-runs/{run_id}", status_code=303)


@app.post("/director-runs/{run_id}/start", response_class=HTMLResponse)
def director_run_start(request: Request, run_id: int) -> RedirectResponse:
    run_autonomous_studio(run_id, use_provider=True)
    return RedirectResponse(f"/director-runs/{run_id}", status_code=303)


@app.get("/director-runs/{run_id}", response_class=HTMLResponse)
def director_run_detail(request: Request, run_id: int) -> HTMLResponse:
    return templates.TemplateResponse("director_run_detail.html", context(request, status=run_status(run_id)))


@app.get("/director-runs/{run_id}/events")
def director_run_events(run_id: int) -> StreamingResponse:
    def stream():
        status = run_status(run_id)
        for event in reversed(status.get("events", [])):
            yield f"event: {event['event_type']}\ndata: {event['message']}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.post("/director-runs/{run_id}/pause", response_class=HTMLResponse)
def director_run_pause(request: Request, run_id: int) -> RedirectResponse:
    set_run_status(run_id, "paused")
    return RedirectResponse(f"/director-runs/{run_id}", status_code=303)


@app.post("/director-runs/{run_id}/resume", response_class=HTMLResponse)
def director_run_resume(request: Request, run_id: int) -> RedirectResponse:
    set_run_status(run_id, "queued")
    run_autonomous_studio(run_id, use_provider=False)
    return RedirectResponse(f"/director-runs/{run_id}", status_code=303)


@app.post("/director-runs/{run_id}/cancel", response_class=HTMLResponse)
def director_run_cancel(request: Request, run_id: int) -> RedirectResponse:
    set_run_status(run_id, "cancelled")
    return RedirectResponse(f"/director-runs/{run_id}", status_code=303)


@app.post("/director-runs/{run_id}/retry/{stage}", response_class=HTMLResponse)
def director_run_retry(request: Request, run_id: int, stage: str) -> RedirectResponse:
    retry_stage(run_id, stage)
    return RedirectResponse(f"/director-runs/{run_id}", status_code=303)


@app.get("/director-runs/{run_id}/questions", response_class=HTMLResponse)
def director_run_questions(request: Request, run_id: int) -> HTMLResponse:
    return templates.TemplateResponse("director_run_questions.html", context(request, status=run_status(run_id)))


@app.get("/storyboard", response_class=HTMLResponse)
def storyboard(request: Request, message: str = "") -> HTMLResponse:
    return templates.TemplateResponse(
        "storyboard.html",
        context(
            request,
            status=director_status(),
            workspace=workspace_summary(),
            cards=list_storyboard_cards(),
            variants=list_storyboard_variants(),
            message=message,
        ),
    )


@app.post("/storyboard/sync", response_class=HTMLResponse)
def storyboard_sync(request: Request) -> RedirectResponse:
    sync_workspace_from_latest_plan()
    return RedirectResponse("/storyboard?message=synced", status_code=303)


@app.post("/storyboard/{shot_number}/decision", response_class=HTMLResponse)
async def storyboard_decision(request: Request, shot_number: str) -> RedirectResponse:
    form = await form_dict(request)
    ok, message = decide_storyboard_card(shot_number, form.get("decision", "planned"), form.get("reason", ""))
    status = "saved" if ok else "error"
    return RedirectResponse(f"/storyboard?message={quote(status + ': ' + message)}", status_code=303)


@app.post("/storyboard/{shot_number}/comment", response_class=HTMLResponse)
async def storyboard_comment(request: Request, shot_number: str) -> RedirectResponse:
    ok, message = comment_storyboard_card(shot_number, (await form_dict(request)).get("comment", ""))
    status = "saved" if ok else "error"
    return RedirectResponse(f"/storyboard?message={quote(status + ': ' + message)}", status_code=303)


@app.post("/storyboard/{shot_number}/generate-local-ai", response_class=HTMLResponse)
async def storyboard_generate_local_ai(request: Request, shot_number: str) -> RedirectResponse:
    form = await form_dict(request)
    ok, message, _variant = generate_storyboard_ai_variant(shot_number, form.get("refinement_text", ""))
    status = "created" if ok else "blocked"
    return RedirectResponse(f"/storyboard?message={quote(status + ': ' + message)}", status_code=303)


@app.get("/animatic", response_class=HTMLResponse)
def animatic(request: Request, message: str = "") -> HTMLResponse:
    latest_runs = list_runs()
    latest_run_id = latest_runs[0]["run_id"] if latest_runs else 1
    return templates.TemplateResponse(
        "animatic.html",
        context(request, workspace=workspace_summary(), latest_run_id=latest_run_id, safe=latest_safe_animatic_context(), message=message),
    )


@app.post("/animatic/build", response_class=HTMLResponse)
def animatic_build(request: Request) -> RedirectResponse:
    build_animatic_v15()
    return RedirectResponse("/animatic?message=sync_calibrated_review_built", status_code=303)


@app.get("/music-analysis", response_class=HTMLResponse)
def music_analysis_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("music_analysis.html", context(request, analysis=music_analysis(), auto_sync=auto_sync_status()))


@app.get("/music-analysis/brain", response_class=HTMLResponse)
def music_brain_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("music_brain.html", context(request, brain=brain_timeline_status()))


@app.get("/shot-plan", response_class=HTMLResponse)
def shot_plan(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("shot_plan.html", context(request, status=director_status()))


@app.get("/production", response_class=HTMLResponse)
def production_command(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("production_command.html", context(request, status=director_status(), workspace=workspace_summary()))


@app.get("/research-assistant", response_class=HTMLResponse)
def research_assistant(request: Request, query: str = "") -> HTMLResponse:
    result = research_search_assistant(query) if query else None
    if query:
        add_research_items(query)
    return templates.TemplateResponse(
        "research_assistant.html",
        context(request, query=query, result=result, items=list_research_items()),
    )


@app.post("/research-assistant/audit", response_class=HTMLResponse)
def research_audit_run(request: Request) -> RedirectResponse:
    write_research_audit()
    return RedirectResponse("/research-assistant?query=mature+side-travel+performance+references", status_code=303)


@app.get("/motion-lab", response_class=HTMLResponse)
def motion_lab(request: Request, message: str = "") -> HTMLResponse:
    return templates.TemplateResponse(
        "motion_lab.html",
        context(request, references=list_motion_references(), analyses=list_motion_analyses(), message=message),
    )


@app.post("/motion-lab/{motion_id}/analyze", response_class=HTMLResponse)
def motion_lab_analyze(request: Request, motion_id: int) -> RedirectResponse:
    ok, message = analyze_motion_reference(motion_id)
    status = "saved" if ok else "error"
    return RedirectResponse(f"/motion-lab?message={quote(status + ': ' + message)}", status_code=303)


@app.get("/captions-voice", response_class=HTMLResponse)
def captions_voice(request: Request, message: str = "") -> HTMLResponse:
    return templates.TemplateResponse(
        "captions_voice.html",
        context(request, lines=list_caption_lines(), voice_tests=list_voice_tests(), message=message),
    )


@app.get("/captions-voice/import", response_class=HTMLResponse)
def captions_voice_import(request: Request, phrase_id: int = 1, message: str = "") -> HTMLResponse:
    return templates.TemplateResponse("voice_import.html", context(request, timing=lyric_timing_summary(), phrase_id=phrase_id, message=message))


@app.post("/captions-voice/import", response_class=HTMLResponse)
async def captions_voice_import_save(request: Request) -> RedirectResponse:
    form = await form_dict(request)
    ok, message, _payload = import_voice_audio_for_phrase(
        int(form.get("phrase_id", "0")),
        form.get("audio_path", ""),
        form.get("provider", "manual_import"),
    )
    status = "saved" if ok else "error"
    return RedirectResponse(f"/captions-voice/sync?message={quote(status + ': ' + message)}", status_code=303)


@app.get("/captions-voice/sync", response_class=HTMLResponse)
def captions_voice_sync(request: Request, message: str = "") -> HTMLResponse:
    return templates.TemplateResponse("voice_sync.html", context(request, sync=voice_sync_summary(), message=message))


@app.post("/captions/{line_id}", response_class=HTMLResponse)
async def caption_update(request: Request, line_id: int) -> RedirectResponse:
    ok, message = update_caption_line(line_id, await form_dict(request))
    status = "saved" if ok else "error"
    return RedirectResponse(f"/captions-voice?message={quote(status + ': ' + message)}", status_code=303)


@app.get("/burmese-language", response_class=HTMLResponse)
def burmese_language(request: Request, message: str = "") -> HTMLResponse:
    return templates.TemplateResponse("burmese_language.html", context(request, summary=burmese_language_summary(), message=message))


@app.post("/burmese-language/build", response_class=HTMLResponse)
def burmese_language_build(request: Request) -> RedirectResponse:
    build_burmese_timeline()
    return RedirectResponse("/burmese-language?message=built", status_code=303)


@app.get("/burmese-language/conversion-review", response_class=HTMLResponse)
def burmese_conversion_review(request: Request, message: str = "") -> HTMLResponse:
    return templates.TemplateResponse(
        "burmese_conversion_review.html",
        context(request, review=conversion_review_summary(), converter=converter_status(), message=message),
    )


@app.post("/burmese-language/conversion-review/{source_line_id:int}", response_class=HTMLResponse)
async def burmese_conversion_review_save(request: Request, source_line_id: int) -> RedirectResponse:
    form = await form_dict(request)
    ok, message = update_conversion_review(source_line_id, form.get("action", ""), form.get("corrected_unicode", ""))
    status = "saved" if ok else "error"
    return RedirectResponse(f"/burmese-language/conversion-review?message={quote(status + ': ' + message)}", status_code=303)


@app.post("/burmese-language/conversion-review/bulk-approve", response_class=HTMLResponse)
def burmese_conversion_bulk_approve(request: Request) -> RedirectResponse:
    result = approve_all_high_confidence_validated()
    return RedirectResponse(f"/burmese-language/conversion-review?message=approved:{result['approved']}", status_code=303)


@app.get("/burmese-language/alignment", response_class=HTMLResponse)
def burmese_alignment(request: Request, message: str = "") -> HTMLResponse:
    return templates.TemplateResponse(
        "burmese_alignment.html",
        context(request, timing=lyric_timing_summary(), validation=validate_phrase_timing(), message=message),
    )


@app.get("/burmese-language/listening-sync", response_class=HTMLResponse)
def burmese_listening_sync(request: Request, message: str = "") -> HTMLResponse:
    return templates.TemplateResponse(
        "listening_sync.html",
        context(request, sync=listening_sync_status(), brain=brain_timeline_status(), message=message),
    )


@app.get("/burmese-language/sync-calibration", response_class=HTMLResponse)
def burmese_sync_calibration(request: Request, message: str = "") -> HTMLResponse:
    return templates.TemplateResponse(
        "sync_calibration.html",
        context(request, calibration=sync_calibration_status(), brain=brain_timeline_status(), message=message),
    )


@app.post("/burmese-language/sync-calibration/apply", response_class=HTMLResponse)
async def burmese_sync_calibration_apply(request: Request) -> RedirectResponse:
    form = await form_dict(request)
    try:
        seconds = float(form.get("seconds", "0"))
    except ValueError:
        seconds = 0.0
    if form.get("approve") == "1":
        approve_global_caption_offset(seconds)
        message = f"approved_global_offset:{seconds}"
    else:
        apply_caption_offset(seconds)
        message = f"applied_offset_delta:{seconds}"
    return RedirectResponse(f"/burmese-language/sync-calibration?message={quote(message)}", status_code=303)


@app.post("/burmese-language/sync-calibration/rebuild-run15", response_class=HTMLResponse)
def burmese_sync_calibration_rebuild_run15(request: Request) -> RedirectResponse:
    build_animatic_v15()
    return RedirectResponse("/animatic?message=run15_sync_calibrated_built", status_code=303)


@app.post("/burmese-language/listening-sync/{phrase_id:int}", response_class=HTMLResponse)
async def burmese_listening_sync_save(request: Request, phrase_id: int) -> RedirectResponse:
    form = await form_dict(request)
    ok, message = update_listening_sync(phrase_id, form.get("status", "uncertain"), form.get("notes", ""))
    status = "saved" if ok else "error"
    return RedirectResponse(f"/burmese-language/listening-sync?message={quote(status + ': ' + message)}", status_code=303)


@app.get("/burmese-language/font-check", response_class=HTMLResponse)
def burmese_font_check(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("font_check.html", context(request, font=font_render_preview()))


@app.get("/auto-sync", response_class=HTMLResponse)
def auto_sync_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("auto_sync.html", context(request, auto_sync=auto_sync_status()))


@app.post("/auto-sync/run", response_class=HTMLResponse)
def auto_sync_run(request: Request) -> RedirectResponse:
    auto_sync_lyrics()
    rebuild_caption_v4()
    return RedirectResponse("/auto-sync?message=auto_sync_complete", status_code=303)


@app.post("/brain-sync/run", response_class=HTMLResponse)
def brain_sync_run(request: Request) -> RedirectResponse:
    build_brain_timeline()
    rebuild_caption_v5()
    return RedirectResponse("/music-analysis/brain?message=brain_sync_complete", status_code=303)


@app.post("/sync-calibration/suggest", response_class=HTMLResponse)
def sync_calibration_suggest(request: Request) -> RedirectResponse:
    generate_offset_candidates()
    build_calibrated_brain_timeline()
    return RedirectResponse("/burmese-language/sync-calibration?message=candidates_updated", status_code=303)


@app.post("/brain-sync/apply-offset", response_class=HTMLResponse)
async def brain_sync_apply_offset(request: Request) -> RedirectResponse:
    form = await form_dict(request)
    try:
        seconds = float(form.get("seconds", "0"))
    except ValueError:
        seconds = 0.0
    result = apply_caption_offset(seconds)
    return RedirectResponse(f"/burmese-language/listening-sync?message=offset_saved:{result['global_caption_delay_seconds']}", status_code=303)


@app.get("/setup/local-asr", response_class=HTMLResponse)
def setup_local_asr(request: Request, message: str = "") -> HTMLResponse:
    return templates.TemplateResponse("setup_local_asr.html", context(request, asr=asr_health(), message=message))


@app.post("/setup/local-asr/run-existing", response_class=HTMLResponse)
def setup_local_asr_run_existing(request: Request) -> RedirectResponse:
    run_local_asr_alignment()
    return RedirectResponse("/setup/local-asr?message=local_asr_checked", status_code=303)


@app.get("/lipsync/brain-readiness", response_class=HTMLResponse)
def lipsync_brain_readiness(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("lipsync_brain_readiness.html", context(request, readiness=brain_lipsync_readiness()))


@app.post("/burmese-language/rebuild-captions-v2", response_class=HTMLResponse)
def burmese_rebuild_captions_v2(request: Request) -> RedirectResponse:
    result = rebuild_caption_v2()
    return RedirectResponse(f"/burmese-language?message={quote('caption_v2_blocked:' + str(result['blocked_count']))}", status_code=303)


@app.get("/lipsync", response_class=HTMLResponse)
def lipsync(request: Request, message: str = "") -> HTMLResponse:
    return templates.TemplateResponse("lipsync.html", context(request, dashboard=lipsync_dashboard(), message=message))


@app.post("/lipsync/plan", response_class=HTMLResponse)
def lipsync_plan_create(request: Request) -> RedirectResponse:
    build_lipsync_plan()
    return RedirectResponse("/lipsync?message=plan_created", status_code=303)


@app.get("/lipsync/shots", response_class=HTMLResponse)
def lipsync_shots(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("lipsync_shots.html", context(request, shots=classify_lipsync_shots()))


@app.get("/lipsync/jobs", response_class=HTMLResponse)
def lipsync_jobs(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("lipsync_jobs.html", context(request, jobs=list_lipsync_jobs()))


@app.get("/lipsync/jobs/new", response_class=HTMLResponse)
def lipsync_job_new(request: Request, shot_id: str = "F01_side_travel_dance") -> HTMLResponse:
    return templates.TemplateResponse("lipsync_job_new.html", context(request, shot_id=shot_id))


@app.post("/lipsync/jobs/new", response_class=HTMLResponse)
async def lipsync_job_create(request: Request) -> RedirectResponse:
    form = await form_dict(request)
    job_id = create_lipsync_job(form.get("shot_id", "F01_side_travel_dance"))
    return RedirectResponse(f"/lipsync/jobs/{job_id}", status_code=303)


@app.get("/lipsync/jobs/{job_id}", response_class=HTMLResponse)
def lipsync_job_detail(request: Request, job_id: int, message: str = "") -> HTMLResponse:
    return templates.TemplateResponse(
        "lipsync_job_detail.html",
        context(request, job=get_lipsync_job(job_id), outputs=lipsync_outputs_for_job(job_id), message=message),
    )


@app.post("/lipsync/jobs/{job_id}/manual-export", response_class=HTMLResponse)
def lipsync_job_manual_export(request: Request, job_id: int) -> RedirectResponse:
    ok, message, _path = create_manual_infinitetalk_export(job_id)
    status = "saved" if ok else "error"
    return RedirectResponse(f"/lipsync/jobs/{job_id}?message={quote(status + ': ' + message)}", status_code=303)


@app.get("/lipsync/jobs/{job_id}/review", response_class=HTMLResponse)
def lipsync_job_review(request: Request, job_id: int) -> HTMLResponse:
    return templates.TemplateResponse("lipsync_job_review.html", context(request, job=get_lipsync_job(job_id), outputs=lipsync_outputs_for_job(job_id)))


@app.get("/lipsync/providers", response_class=HTMLResponse)
def lipsync_providers(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("lipsync_providers.html", context(request, providers=refresh_lipsync_provider_health()))


@app.get("/setup/infinitetalk", response_class=HTMLResponse)
def setup_infinitetalk(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("setup_infinitetalk.html", context(request, providers=refresh_lipsync_provider_health()))


@app.post("/voice-tests", response_class=HTMLResponse)
async def voice_test_create(request: Request) -> RedirectResponse:
    ok, message = create_voice_test(await form_dict(request))
    status = "saved" if ok else "error"
    return RedirectResponse(f"/captions-voice?message={quote(status + ': ' + message)}", status_code=303)


@app.get("/advanced", response_class=HTMLResponse)
def dashboard(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "dashboard.html",
        context(
            request,
            engine=engine_status(),
            product=product_status(),
            shot_packs=list_shot_packs(),
            generated=list_generated_requests(),
            connectors=connector_status(),
            workflow=workflow_summary(),
            result_counts=result_counts(),
        ),
    )


@app.get("/workflow", response_class=HTMLResponse)
def workflow(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("workflow.html", context(request, workflow=workflow_summary()))


@app.get("/jobs", response_class=HTMLResponse)
def jobs(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("jobs.html", context(request, jobs=list_jobs()))


@app.get("/exports", response_class=HTMLResponse)
def exports(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("exports.html", context(request, exports=list_manual_exports()))


@app.get("/results", response_class=HTMLResponse)
def results(request: Request, show_tests: str = "") -> HTMLResponse:
    return templates.TemplateResponse(
        "results.html",
        context(request, results=list_results(show_tests == "1"), counts=result_counts(), show_tests=show_tests == "1"),
    )


@app.get("/results/import", response_class=HTMLResponse)
def results_import(request: Request, message: str = "") -> HTMLResponse:
    return templates.TemplateResponse("result_import.html", context(request, exports=list_manual_exports(), message=message))


@app.post("/results/import", response_class=HTMLResponse)
async def results_import_submit(request: Request) -> RedirectResponse:
    form = await form_dict(request)
    ok, message, result_id = import_result_from_path(
        form.get("source_path", ""),
        form.get("shot_id", "F01_side_travel_dance"),
        int(form.get("job_id") or 0),
        int(form.get("export_id") or 0),
        form.get("renderer", "manual"),
        form.get("is_test") == "on",
    )
    if ok and result_id is not None:
        return RedirectResponse(f"/results/{result_id}", status_code=303)
    return RedirectResponse(f"/results/import?message={quote('error: ' + message)}", status_code=303)


@app.get("/results/{result_id}", response_class=HTMLResponse)
def result_detail(request: Request, result_id: int) -> HTMLResponse:
    return templates.TemplateResponse("result_detail.html", context(request, result=get_result(result_id)))


@app.get("/results/{result_id}/review", response_class=HTMLResponse)
def result_review(request: Request, result_id: int, message: str = "") -> HTMLResponse:
    return templates.TemplateResponse("result_review.html", context(request, result=get_result(result_id), message=message))


@app.post("/results/{result_id}/review", response_class=HTMLResponse)
async def result_review_submit(request: Request, result_id: int) -> RedirectResponse:
    ok, message = submit_result_review(result_id, await form_dict(request))
    status = "saved" if ok else "error"
    return RedirectResponse(f"/results/{result_id}/review?message={quote(status + ': ' + message)}", status_code=303)


@app.get("/results/{result_id}/decision", response_class=HTMLResponse)
def result_decision(request: Request, result_id: int, message: str = "") -> HTMLResponse:
    return templates.TemplateResponse("result_decision.html", context(request, result=get_result(result_id), message=message))


@app.post("/results/{result_id}/decision", response_class=HTMLResponse)
async def result_decision_submit(request: Request, result_id: int) -> RedirectResponse:
    ok, message = submit_result_decision(result_id, await form_dict(request))
    status = "saved" if ok else "error"
    return RedirectResponse(f"/results/{result_id}/decision?message={quote(status + ': ' + message)}", status_code=303)


@app.get("/jobs/{shot_id}/{job_id}/results", response_class=HTMLResponse)
def job_results(request: Request, shot_id: str, job_id: int) -> HTMLResponse:
    linked = [result for result in list_results(True) if result["shot_id"] == shot_id and result["job_id"] == job_id]
    return templates.TemplateResponse("results.html", context(request, results=linked, counts=result_counts(), show_tests=True))


@app.get("/result-media/{media_path:path}")
def result_media(media_path: str) -> Response:
    root = RESULT_MEDIA_ROOT.resolve()
    path = (root / media_path).resolve()
    if not str(path).startswith(str(root)) or not path.is_file():
        return Response(status_code=404)
    return FileResponse(str(path))


@app.get("/director-assets/animatics/{run_id}/{filename}")
def director_animatic_asset(run_id: str, filename: str) -> Response:
    return safe_director_asset_response(f"animatics/{run_id}/{filename}")


@app.get("/director-assets/{asset_path:path}")
def director_assets(asset_path: str) -> Response:
    return safe_director_asset_response(asset_path)


def safe_director_asset_response(asset_path: str) -> Response:
    path, status, message = resolve_director_asset(asset_path)
    if path is not None:
        return FileResponse(str(path))
    body = (
        "<!doctype html><html><head><meta charset=\"utf-8\"><title>Director Asset</title></head>"
        "<body><h1>Director asset unavailable</h1>"
        f"<p>{message}</p><p>Requested: <code>{asset_path}</code></p>"
        "<p><a href=\"/animatic\">Open latest safe animatic</a></p></body></html>"
    )
    return HTMLResponse(body, status_code=410 if "animatics/11/" in asset_path and status == 404 else status)


@app.get("/exports/new/{shot_id}/{job_id}", response_class=HTMLResponse)
def exports_new(request: Request, shot_id: str, job_id: int, message: str = "") -> HTMLResponse:
    return templates.TemplateResponse(
        "export_new.html",
        context(request, shot_id=shot_id, job=get_job(shot_id, job_id), message=message),
    )


@app.post("/exports/new/{shot_id}/{job_id}", response_class=HTMLResponse)
async def exports_create(request: Request, shot_id: str, job_id: int) -> RedirectResponse:
    form = await form_dict(request)
    ok, message, export_id = create_manual_export(shot_id, job_id, form)
    if ok and export_id is not None:
        return RedirectResponse(f"/exports/{shot_id}/{export_id}", status_code=303)
    return RedirectResponse(f"/exports/new/{shot_id}/{job_id}?message={quote('error: ' + message)}", status_code=303)


@app.get("/exports/{shot_id}/{export_id}", response_class=HTMLResponse)
def export_detail(request: Request, shot_id: str, export_id: int) -> HTMLResponse:
    return templates.TemplateResponse(
        "export_detail.html",
        context(request, shot_id=shot_id, export=get_manual_export(shot_id, export_id)),
    )


@app.get("/jobs/new/{shot_id}", response_class=HTMLResponse)
def jobs_new(request: Request, shot_id: str, message: str = "") -> HTMLResponse:
    return templates.TemplateResponse(
        "job_new.html",
        context(
            request,
            shot_id=shot_id,
            connectors=connector_records(),
            requests=generated_request_options(shot_id),
            message=message,
        ),
    )


@app.post("/jobs/new/{shot_id}", response_class=HTMLResponse)
async def jobs_create(request: Request, shot_id: str) -> RedirectResponse:
    ok, message, job_id = create_job(shot_id, await form_dict(request))
    if ok and job_id is not None:
        return RedirectResponse(f"/jobs/{shot_id}/{job_id}", status_code=303)
    return RedirectResponse(f"/jobs/new/{shot_id}?message={quote('error: ' + message)}", status_code=303)


@app.get("/jobs/{shot_id}/{job_id}", response_class=HTMLResponse)
def job_detail(request: Request, shot_id: str, job_id: int, message: str = "") -> HTMLResponse:
    return templates.TemplateResponse(
        "job_detail.html",
        context(request, shot_id=shot_id, job=get_job(shot_id, job_id), message=message),
    )


@app.get("/jobs/{shot_id}/{job_id}/readiness", response_class=HTMLResponse)
def job_readiness_detail(request: Request, shot_id: str, job_id: int) -> HTMLResponse:
    return templates.TemplateResponse(
        "job_readiness.html",
        context(request, shot_id=shot_id, readiness=job_readiness(shot_id, job_id)),
    )


@app.post("/jobs/{shot_id}/{job_id}/dry-run", response_class=HTMLResponse)
def job_dry_run(request: Request, shot_id: str, job_id: int) -> RedirectResponse:
    ok, message = run_job_dry_run(shot_id, job_id)
    status = "saved" if ok else "error"
    return RedirectResponse(f"/jobs/{shot_id}/{job_id}?message={quote(status + ': ' + message)}", status_code=303)


@app.get("/product", response_class=HTMLResponse)
def product(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("product.html", context(request, documents=product_documents()))


@app.get("/shot-packs", response_class=HTMLResponse)
def shot_packs(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("shot_packs.html", context(request, shot_packs=list_shot_packs()))


@app.get("/shot-packs/{shot_id}", response_class=HTMLResponse)
def shot_pack_detail(request: Request, shot_id: str) -> HTMLResponse:
    return templates.TemplateResponse("shot_pack_detail.html", context(request, pack=get_shot_pack(shot_id)))


@app.get("/motion-references", response_class=HTMLResponse)
def motion_references(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "motion_references.html",
        context(request, references=list_motion_references()),
    )


@app.get("/motion-references/new", response_class=HTMLResponse)
def motion_references_new(request: Request, message: str = "") -> HTMLResponse:
    return templates.TemplateResponse("motion_reference_new.html", context(request, message=message))


@app.post("/motion-references/new", response_class=HTMLResponse)
async def motion_references_create(request: Request) -> RedirectResponse:
    ok, message, _motion_id = create_motion_reference(await form_dict(request))
    if ok:
        return RedirectResponse(f"/motion-references?message={quote('saved: ' + message)}", status_code=303)
    return RedirectResponse(f"/motion-references/new?message={quote('error: ' + message)}", status_code=303)


@app.get("/shot-packs/{shot_id}/motion-reference", response_class=HTMLResponse)
def shot_pack_motion_reference(request: Request, shot_id: str) -> HTMLResponse:
    return templates.TemplateResponse(
        "motion_reference_detail.html",
        context(request, shot_id=shot_id, reference=get_latest_motion_reference(shot_id)),
    )


@app.get("/generated-requests", response_class=HTMLResponse)
def generated_requests(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "generated_requests.html", context(request, packages=list_generated_requests(), selected=None)
    )


@app.get("/generated-requests/{shot_id}/{filename}", response_class=HTMLResponse)
def generated_request_file(request: Request, shot_id: str, filename: str) -> HTMLResponse:
    return templates.TemplateResponse(
        "generated_requests.html",
        context(request, packages=list_generated_requests(), selected=get_generated_file(shot_id, filename)),
    )


@app.get("/reference-library", response_class=HTMLResponse)
def reference_library(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("reference_library.html", context(request, reference=reference_status()))


@app.get("/connectors", response_class=HTMLResponse)
def connectors(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("connectors.html", context(request, connectors=connector_status()))


@app.get("/connectors/status", response_class=HTMLResponse)
def connectors_status(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "connector_status.html",
        context(request, connectors=connector_status(), records=connector_records()),
    )


@app.get("/approval-gate", response_class=HTMLResponse)
def approval_gate(request: Request) -> HTMLResponse:
    return RedirectResponse("/approval-gate/F01_side_travel_dance", status_code=303)


@app.get("/approval-gate/{shot_id}", response_class=HTMLResponse)
def approval_gate_detail(request: Request, shot_id: str, message: str = "") -> HTMLResponse:
    selected = get_generated_file(shot_id, "00_APPROVAL_GATE.md")
    return templates.TemplateResponse(
        "approval_gate.html",
        context(request, selected=selected, approvals=list_approvals(shot_id), shot_id=shot_id, message=message),
    )


@app.post("/approval-gate/{shot_id}", response_class=HTMLResponse)
async def approval_gate_submit(request: Request, shot_id: str) -> RedirectResponse:
    ok, message = create_approval(shot_id, await form_dict(request))
    status = "saved" if ok else "error"
    return RedirectResponse(f"/approval-gate/{shot_id}?message={quote(status + ': ' + message)}", status_code=303)


@app.get("/qc", response_class=HTMLResponse)
def qc(request: Request) -> HTMLResponse:
    return RedirectResponse("/qc/F01_side_travel_dance", status_code=303)


@app.get("/qc/{shot_id}", response_class=HTMLResponse)
def qc_detail(request: Request, shot_id: str, message: str = "") -> HTMLResponse:
    selected = get_generated_file(shot_id, "09_QC_SCORECARD.md")
    return templates.TemplateResponse(
        "qc.html",
        context(request, selected=selected, reviews=list_qc_reviews(shot_id), shot_id=shot_id, message=message),
    )


@app.post("/qc/{shot_id}", response_class=HTMLResponse)
async def qc_submit(request: Request, shot_id: str) -> RedirectResponse:
    ok, message = create_qc_review(shot_id, await form_dict(request))
    status = "saved" if ok else "error"
    return RedirectResponse(f"/qc/{shot_id}?message={quote(status + ': ' + message)}", status_code=303)


@app.get("/moodboards", response_class=HTMLResponse)
def moodboards(request: Request, message: str = "") -> HTMLResponse:
    return templates.TemplateResponse(
        "moodboards.html",
        context(request, moodboards=list_moodboards(), message=message),
    )


@app.get("/moodboards/new", response_class=HTMLResponse)
def moodboards_new(request: Request, message: str = "") -> HTMLResponse:
    return templates.TemplateResponse("moodboard_new.html", context(request, message=message))


@app.post("/moodboards/new", response_class=HTMLResponse)
async def moodboards_create(request: Request) -> RedirectResponse:
    ok, message = create_moodboard(await form_dict(request))
    if ok:
        return RedirectResponse(f"/moodboards?message={quote('saved: ' + message)}", status_code=303)
    return RedirectResponse(f"/moodboards/new?message={quote('error: ' + message)}", status_code=303)


@app.get("/audit-log", response_class=HTMLResponse)
def audit_log(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("audit_log.html", context(request, logs=list_audit_logs()))
