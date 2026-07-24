from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.audio.brain_sync_service import build_calibrated_brain_timeline
from app.audio.sync_offset_service import sync_calibration_status
from app.config import ENGINE_ROOT, REPO_ROOT
from app.services.db import connect, initialize_database
from app.studio_loop.acceptance_gate import evaluate_acceptance
from app.studio_loop.budget_guard import budget_guard
from app.studio_loop.capability_router import capability_matrix, route_for_task
from app.studio_loop.defect_detector import detect_defects
from app.studio_loop.evaluator import evaluate_current_output
from app.studio_loop.loop_state import loop_eval_dir, read_json, utc_now, write_json, write_loop_state, write_production_brain
from app.studio_loop.repair_executor import execute_safe_repairs
from app.studio_loop.repair_planner import plan_repairs
from app.studio_loop.root_cause_analyzer import analyze_root_causes
from app.studio_loop.stage_registry import production_graph, stage_list


DEFAULT_STUDIO_IDEA = (
    "Create and finish the strongest possible cinematic Burmese music video from everything already present in this project. "
    "Use approved identity, wardrobe, bar, Burmese world, song, lyrics, failures and production evidence. "
    "Research, direct, assemble, watch, diagnose, repair and stop only for consolidated approval."
)


def create_studio_loop(idea: str, project_path: str, max_iterations: int = 5) -> int:
    initialize_database()
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO studio_loops(project_path, idea, status, max_iterations, next_action)
            VALUES (?, ?, 'understanding', ?, 'Starting self-driving production loop')
            """,
            (project_path, idea, max_iterations),
        )
        loop_id = int(cur.lastrowid)
    _event(loop_id, "loop_created", "Studio loop created from one prompt.", {"idea": idea})
    return loop_id


def run_studio_loop(loop_id: int, max_auto_iterations: int = 2) -> dict[str, Any]:
    loop = studio_loop_status(loop_id)
    if not loop:
        raise ValueError(f"studio loop {loop_id} not found")
    iterations = min(max_auto_iterations, int(loop.get("max_iterations") or 5))
    final: dict[str, Any] = {}
    for iteration in range(1, iterations + 1):
        _iteration(loop_id, iteration, "running", "PLAN -> EXECUTE -> BUILD OUTPUT -> EVALUATE -> REPAIR")
        _run_stages(loop_id, iteration)
        brain = build_production_brain(loop_id, iteration)
        evaluation = evaluate_current_output(loop_id, iteration)
        defects = [defect.__dict__ for defect in detect_defects(evaluation)]
        causes = analyze_root_causes(defects)
        repairs = [repair.__dict__ for repair in plan_repairs(defects)]
        repair_results = execute_safe_repairs(repairs) if iteration == 1 else []
        acceptance = evaluate_acceptance(evaluation, defects)
        final = _write_iteration_artifacts(loop_id, iteration, brain, evaluation, defects, causes, repairs, repair_results, acceptance)
        status = "repairing" if repair_results and iteration < iterations and acceptance["status"] != "acceptance_passed" else acceptance["status"]
        _update_loop(loop_id, status, iteration, evaluation.get("score", 0), acceptance["next_action"], final["latest_artifact"], acceptance)
        _iteration(loop_id, iteration, "completed", f"Score {evaluation.get('score')} status {acceptance['status']}")
        if acceptance["status"] in {"acceptance_passed", "awaiting_approval", "stopped_with_blockers"} and iteration > 1:
            break
    return studio_loop_detail(loop_id)


def continue_studio_loop(project_path: str) -> dict[str, Any]:
    latest = latest_loop()
    if not latest:
        loop_id = create_studio_loop(DEFAULT_STUDIO_IDEA, project_path)
    else:
        loop_id = int(latest["loop_id"])
    return run_studio_loop(loop_id)


def build_production_brain(loop_id: int, iteration: int) -> dict[str, Any]:
    brain_timeline = build_calibrated_brain_timeline()
    graph = production_graph()
    brain = {
        "version": "v2.0",
        "loop_id": loop_id,
        "iteration": iteration,
        "brief": studio_loop_status(loop_id).get("idea", ""),
        "concepts": _read_optional(ENGINE_ROOT / "director-plan" / "CREATIVE_CONCEPTS.md"),
        "evidence": _read_optional(ENGINE_ROOT / "state" / "EVIDENCE_GRAPH.json"),
        "research": {"status": "local_records_and_public_benchmark_notes", "items": _research_summary()},
        "song_structure": _read_optional(ENGINE_ROOT / "state" / "MUSIC_ANALYSIS.json"),
        "waveform": "local waveform/energy analysis",
        "energy": "stored in MUSIC_ANALYSIS.json",
        "vocal_regions": brain_timeline.get("song_sections", []),
        "lyrics": brain_timeline.get("events", []),
        "approved_unicode": [event.get("approved_unicode") for event in brain_timeline.get("events", [])],
        "pronunciation": [event.get("pronunciation_helper") for event in brain_timeline.get("events", [])],
        "meaning": _read_optional(ENGINE_ROOT / "state" / "LYRIC_MEANING_EMOTION_MAP.json"),
        "emotional_arc": "phrase-level heuristic/director-inferred; not automatic emotion recognition",
        "characters": {"wife_performer": "consenting adult performer; private identity assets restricted"},
        "identity": {"approved_refs": ["REF-A1", "REF-A2"], "privacy": "exact approved only"},
        "wardrobe": {"locked": "deep-red one-shoulder Burmese-inspired dress"},
        "locations": {"locked": "approved dark Finnish bar, winter window"},
        "cultural_details": {"locked": "Burmese art/craft visual world; avoid generic Asian drift"},
        "shot_graph": graph,
        "visual_grammar": _read_optional(ENGINE_ROOT / "state" / "PROJECT_STATE.json"),
        "camera": "from storyboard visual grammar records",
        "lighting": "amber/crimson practicals and cold winter window contrast",
        "blocking": "from storyboard cards and diagrams",
        "performance": "restrained mature blues/jazz emotional pressure",
        "movement": "motion-reference controlled; no kung fu/K-pop/TikTok",
        "storyboard_assets": {"origin": "composite/diagram unless model approved"},
        "voice": {"status": "not_tested_no_voice_audio"},
        "captions": {"version": "v6", "status": "review_only_sync_calibrated"},
        "lip_sync": {"status": "blocked_until_sync_and_provider_ready"},
        "editing": {"canonical": "full-song ffmpeg/OTIO handoff"},
        "renderers": capability_matrix(),
        "qc": {"mandatory_gates": "defined in studio evaluator"},
        "defects": [],
        "repairs": [],
        "approvals": [],
        "final_state": "not_accepted",
        "metadata": {
            "source": "Director OS local project evidence",
            "confidence": 0.72,
            "status": "active",
            "version": "v2.0",
            "dependencies": ["PRODUCTION_BRAIN_TIMELINE.json", "Run 15 animatic", "v6 captions"],
            "privacy": "local_first_no_upload",
            "rights": "approved/user-owned assets only",
            "generated_by": "studio_loop.orchestrator",
            "evaluated_by": "studio_loop.evaluator",
        },
    }
    write_production_brain(brain)
    return brain


def studio_loop_status(loop_id: int | None = None) -> dict[str, Any]:
    initialize_database()
    with connect() as conn:
        if loop_id is None:
            row = conn.execute("SELECT * FROM studio_loops ORDER BY loop_id DESC LIMIT 1").fetchone()
        else:
            row = conn.execute("SELECT * FROM studio_loops WHERE loop_id = ?", (loop_id,)).fetchone()
    return dict(row) if row else {}


def latest_loop() -> dict[str, Any]:
    return studio_loop_status(None)


def studio_loop_detail(loop_id: int) -> dict[str, Any]:
    status = studio_loop_status(loop_id)
    eval_dir = loop_eval_dir(loop_id)
    detail = {
        "loop": status,
        "state": read_json(ENGINE_ROOT / "state" / "STUDIO_LOOP_STATE.json"),
        "evaluation": read_json(eval_dir / "EVALUATION.json"),
        "defects": read_json(eval_dir / "DEFECTS.json", {"defects": []}),
        "repairs": read_json(eval_dir / "REPAIRS.json", {"repairs": []}),
        "acceptance": read_json(eval_dir / "FINAL_ACCEPTANCE.json"),
        "artifacts": _artifacts(loop_id),
        "events": _events(loop_id),
    }
    return detail


def list_studio_loops() -> list[dict[str, Any]]:
    initialize_database()
    with connect() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM studio_loops ORDER BY loop_id DESC").fetchall()]


def cancel_studio_loop(loop_id: int) -> dict[str, Any]:
    _update_loop(loop_id, "cancelled", studio_loop_status(loop_id).get("current_iteration", 0), 0, "Cancelled by user.", "", {})
    _event(loop_id, "cancelled", "Studio loop cancelled.", {})
    return studio_loop_detail(loop_id)


def approve_studio_loop(approval_id: int) -> dict[str, Any]:
    initialize_database()
    with connect() as conn:
        row = conn.execute("SELECT * FROM studio_loop_approvals WHERE approval_id = ?", (approval_id,)).fetchone()
        if not row:
            return {"ok": False, "message": "approval not found"}
        conn.execute("UPDATE studio_loop_approvals SET status='approved', decided_at=CURRENT_TIMESTAMP WHERE approval_id=?", (approval_id,))
    return {"ok": True, "approval_id": approval_id}


def studio_loop_report(loop_id: int) -> str:
    report = loop_eval_dir(loop_id) / "STUDIO_LOOP_REPORT.md"
    detail = studio_loop_detail(loop_id)
    lines = [
        f"# Studio Loop {loop_id} Report",
        "",
        f"Status: `{detail['loop'].get('status')}`",
        f"Score: `{detail['loop'].get('quality_score')}`",
        f"Next action: {detail['loop'].get('next_action')}",
        "",
        "## Defects",
    ]
    for defect in detail["defects"].get("defects", []):
        lines.append(f"- `{defect['code']}` {defect['severity']}: {defect['symptom']}")
    lines.extend(["", "## Repairs"])
    for repair in detail["repairs"].get("repairs", []):
        lines.append(f"- `{repair.get('repair_action') or repair.get('action')}` {repair['status']}: {repair['summary']}")
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with connect() as conn:
        conn.execute(
            "INSERT INTO studio_loop_final_reports(loop_id, path, acceptance_status, summary) VALUES (?, ?, ?, ?)",
            (
                loop_id,
                str(report),
                detail["loop"].get("status") or "unknown",
                detail["loop"].get("next_action") or "",
            ),
        )
    return str(report)


def _run_stages(loop_id: int, iteration: int) -> None:
    for stage in stage_list():
        provider = route_for_task(stage)
        _stage(loop_id, iteration, stage, "completed", provider.get("provider", "local"), f"{stage} completed with {provider.get('classification')}", provider)


def _write_iteration_artifacts(
    loop_id: int,
    iteration: int,
    brain: dict[str, Any],
    evaluation: dict[str, Any],
    defects: list[dict[str, Any]],
    causes: list[dict[str, Any]],
    repairs: list[dict[str, Any]],
    repair_results: list[dict[str, Any]],
    acceptance: dict[str, Any],
) -> dict[str, Any]:
    eval_dir = loop_eval_dir(loop_id)
    previous_repairs = read_json(eval_dir / "REPAIRS.json", {"repair_history": []})
    repair_history = list(previous_repairs.get("repair_history", []))
    if repair_results:
        repair_history.append({"iteration": iteration, "repair_results": repair_results})
    write_json(eval_dir / "EVALUATION.json", evaluation)
    write_json(eval_dir / "DEFECTS.json", {"defects": defects, "root_causes": causes})
    write_json(eval_dir / "REPAIRS.json", {"repairs": repairs, "repair_results": repair_results, "repair_history": repair_history})
    write_json(eval_dir / "FINAL_ACCEPTANCE.json", acceptance)
    _persist_evaluation_rows(loop_id, iteration, evaluation, defects, repairs)
    state = {
        "version": "v2.0",
        "loop_id": loop_id,
        "iteration": iteration,
        "status": acceptance["status"],
        "quality_score": evaluation.get("score"),
        "brain_path": str(ENGINE_ROOT / "state" / "PRODUCTION_BRAIN.json"),
        "evaluation_path": str(eval_dir / "EVALUATION.json"),
        "defects_path": str(eval_dir / "DEFECTS.json"),
        "repairs_path": str(eval_dir / "REPAIRS.json"),
        "acceptance_path": str(eval_dir / "FINAL_ACCEPTANCE.json"),
        "budget": budget_guard(),
        "updated_at": utc_now(),
    }
    write_loop_state(state)
    _artifact(loop_id, iteration, "production_brain", ENGINE_ROOT / "state" / "PRODUCTION_BRAIN.json", "local")
    _artifact(loop_id, iteration, "evaluation", eval_dir / "EVALUATION.json", "local")
    _artifact(loop_id, iteration, "acceptance", eval_dir / "FINAL_ACCEPTANCE.json", "local")
    for approval in acceptance.get("approvals_required", []):
        _approval(loop_id, approval)
    return {"latest_artifact": str(eval_dir / "EVALUATION.json"), "state": state}


def _persist_evaluation_rows(loop_id: int, iteration: int, evaluation: dict[str, Any], defects: list[dict[str, Any]], repairs: list[dict[str, Any]]) -> None:
    eval_path = str(loop_eval_dir(loop_id) / "EVALUATION.json")
    with connect() as conn:
        conn.execute(
            "INSERT INTO studio_loop_evaluations(loop_id, iteration_number, score, status, path, summary) VALUES (?, ?, ?, ?, ?, ?)",
            (loop_id, iteration, evaluation.get("score", 0), evaluation.get("status", "unknown"), eval_path, f"Evaluated animatic {evaluation.get('active_animatic_version')}"),
        )
        for defect in defects:
            conn.execute(
                "INSERT INTO studio_loop_defects(loop_id, iteration_number, defect_code, severity, symptom, root_cause, affected_artifact, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    loop_id,
                    iteration,
                    defect["code"],
                    defect["severity"],
                    defect["symptom"],
                    defect["root_cause"],
                    defect.get("affected_artifact", ""),
                    json.dumps(defect.get("metadata", {}), ensure_ascii=False),
                ),
            )
        for repair in repairs:
            conn.execute(
                "INSERT INTO studio_loop_repairs(loop_id, iteration_number, defect_code, repair_action, status, approval_required, summary, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    loop_id,
                    iteration,
                    repair["defect_code"],
                    repair["action"],
                    repair["status"],
                    1 if repair.get("approval_required") else 0,
                    repair.get("summary", ""),
                    json.dumps(repair.get("metadata", {}), ensure_ascii=False),
                ),
            )


def _update_loop(loop_id: int, status: str, iteration: int, score: float, next_action: str, latest_artifact: str, acceptance: dict[str, Any]) -> None:
    approval_required = json.dumps(acceptance.get("approvals_required", []), ensure_ascii=False)
    initialize_database()
    with connect() as conn:
        conn.execute(
            """
            UPDATE studio_loops
            SET status=?, current_iteration=?, quality_score=?, acceptance_status=?, approval_required=?,
                latest_artifact=?, next_action=?, updated_at=CURRENT_TIMESTAMP
            WHERE loop_id=?
            """,
            (status, iteration, score, acceptance.get("status", status), approval_required, latest_artifact, next_action, loop_id),
        )
    _event(loop_id, "loop_status", f"Loop status: {status}", {"score": score, "next_action": next_action})


def _iteration(loop_id: int, iteration: int, status: str, summary: str) -> None:
    initialize_database()
    with connect() as conn:
        existing = conn.execute("SELECT iteration_id FROM studio_loop_iterations WHERE loop_id=? AND iteration_number=?", (loop_id, iteration)).fetchone()
        if existing:
            conn.execute(
                "UPDATE studio_loop_iterations SET status=?, completed_at=CURRENT_TIMESTAMP, summary=? WHERE iteration_id=?",
                (status, summary, existing["iteration_id"]),
            )
        else:
            conn.execute(
                "INSERT INTO studio_loop_iterations(loop_id, iteration_number, status, summary) VALUES (?, ?, ?, ?)",
                (loop_id, iteration, status, summary),
            )


def _stage(loop_id: int, iteration: int, name: str, status: str, provider: str, summary: str, metadata: dict[str, Any]) -> None:
    initialize_database()
    with connect() as conn:
        conn.execute(
            "INSERT INTO studio_loop_stages(loop_id, iteration_number, stage_name, status, provider, completed_at, summary, metadata) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?)",
            (loop_id, iteration, name, status, provider, summary, json.dumps(metadata, ensure_ascii=False)),
        )


def _artifact(loop_id: int, iteration: int, artifact_type: str, path: Path, origin: str) -> None:
    initialize_database()
    with connect() as conn:
        conn.execute(
            "INSERT INTO studio_loop_artifacts(loop_id, iteration_number, artifact_type, path, origin, status) VALUES (?, ?, ?, ?, ?, ?)",
            (loop_id, iteration, artifact_type, str(path), origin, "created" if path.exists() else "missing"),
        )


def _approval(loop_id: int, approval: dict[str, Any]) -> None:
    initialize_database()
    with connect() as conn:
        exists = conn.execute(
            "SELECT approval_id FROM studio_loop_approvals WHERE loop_id=? AND approval_type=? AND status='pending'",
            (loop_id, approval["approval_type"]),
        ).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO studio_loop_approvals(loop_id, approval_type, summary, status, metadata) VALUES (?, ?, ?, ?, ?)",
                (loop_id, approval["approval_type"], approval["summary"], approval.get("status", "pending"), json.dumps(approval, ensure_ascii=False)),
            )


def _event(loop_id: int, event_type: str, summary: str, metadata: dict[str, Any]) -> None:
    initialize_database()
    with connect() as conn:
        conn.execute(
            "INSERT INTO studio_loop_events(loop_id, event_type, summary, metadata) VALUES (?, ?, ?, ?)",
            (loop_id, event_type, summary, json.dumps(metadata, ensure_ascii=False)),
        )


def _artifacts(loop_id: int) -> list[dict[str, Any]]:
    with connect() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM studio_loop_artifacts WHERE loop_id=? ORDER BY artifact_id DESC", (loop_id,)).fetchall()]


def _events(loop_id: int) -> list[dict[str, Any]]:
    with connect() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM studio_loop_events WHERE loop_id=? ORDER BY event_id DESC LIMIT 100", (loop_id,)).fetchall()]


def _research_summary() -> dict[str, Any]:
    return {
        "focal_benchmark": str(REPO_ROOT / "director-os-research/FOCAL_PRODUCT_BENCHMARK.md"),
        "pixelle_audit": str(REPO_ROOT / "director-os-research/PIXELLE_VIDEO_CODE_AUDIT.md"),
        "used_by_loop": ["one-prompt graph", "task history", "self-evaluation", "repair loop"],
    }


def _read_optional(path: Path) -> Any:
    if not path.exists():
        return {"status": "missing", "path": str(path)}
    if path.suffix == ".json":
        return read_json(path)
    return {"path": str(path), "summary": path.read_text(encoding="utf-8", errors="ignore")[:1200]}
