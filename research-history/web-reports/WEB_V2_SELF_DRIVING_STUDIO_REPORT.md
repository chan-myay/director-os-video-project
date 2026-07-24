# Director OS v2.0 Self-Driving Studio Report

## Summary

Director OS v2.0 adds the first working self-driving production loop over the existing Director OS stack.

The loop now performs:

1. one-prompt loop creation
2. production graph creation
3. capability routing
4. shared production brain creation
5. local preview evaluation
6. defect classification
7. root-cause analysis
8. safe local repair planning and execution
9. rebuild and re-evaluation
10. acceptance gate calculation
11. consolidated approval stop

No private media upload, paid API call, substantial model download, storyboard model install, voice model install, InfiniteTalk install, or destructive source-media operation was performed.

## Existing Components Reused

v2.0 reuses:

- project archaeology and state files
- approved/rejected evidence memory
- Director Plan and storyboard records
- visual grammar records
- full-song animatic builder
- Run 15 sync-calibrated preview
- Burmese lyric preservation and conversion state
- music waveform and energy analysis
- production brain timeline
- caption v6 exports
- lip-sync readiness planner
- local capability/status records
- privacy/spend gates
- audit and QC infrastructure

## New Components

Created:

- `director-os-web/app/studio_loop/orchestrator.py`
- `director-os-web/app/studio_loop/loop_state.py`
- `director-os-web/app/studio_loop/stage_registry.py`
- `director-os-web/app/studio_loop/capability_router.py`
- `director-os-web/app/studio_loop/evaluator.py`
- `director-os-web/app/studio_loop/defect_detector.py`
- `director-os-web/app/studio_loop/root_cause_analyzer.py`
- `director-os-web/app/studio_loop/repair_planner.py`
- `director-os-web/app/studio_loop/repair_executor.py`
- `director-os-web/app/studio_loop/acceptance_gate.py`
- `director-os-web/app/studio_loop/budget_guard.py`
- `director-os-web/app/studio_loop/approval_gate.py`
- `director-os-web/app/studio_loop/artifact_registry.py`
- `director-os-web/app/studio_loop/event_stream.py`
- `director-os-web/app/studio_loop/schemas.py`

Created routes:

- `/studio-loop`
- `/studio-loop/{loop_id}`
- `/studio-loop/{loop_id}/live`
- `/studio-loop/{loop_id}/artifacts`
- `/studio-loop/{loop_id}/evaluation`
- `/studio-loop/{loop_id}/repairs`
- `/studio-loop/{loop_id}/approvals`

Created CLI:

- `tools/director-os studio-create "<idea>" --project /Users/chan/song-video-project`
- `tools/director-os studio-continue /Users/chan/song-video-project`
- `tools/director-os studio-status /Users/chan/song-video-project`
- `tools/director-os studio-status /Users/chan/song-video-project --json`
- `tools/director-os studio-watch <loop_id>`
- `tools/director-os studio-evaluate <loop_id>`
- `tools/director-os studio-repair <loop_id>`
- `tools/director-os studio-resume <loop_id>`
- `tools/director-os studio-cancel <loop_id>`
- `tools/director-os studio-approve <approval_id>`
- `tools/director-os studio-report <loop_id>`

## Database

Added tables:

- `studio_loops`
- `studio_loop_iterations`
- `studio_loop_stages`
- `studio_loop_artifacts`
- `studio_loop_evaluations`
- `studio_loop_defects`
- `studio_loop_repairs`
- `studio_loop_approvals`
- `studio_loop_costs`
- `studio_loop_events`
- `studio_loop_final_reports`

## Shared Brain

Created:

- `director-os/state/PRODUCTION_BRAIN.json`
- `director-os/state/STUDIO_LOOP_STATE.json`

The production brain links:

- brief
- concepts
- evidence
- research pointers
- music analysis
- vocal regions
- lyrics
- approved Unicode
- pronunciation
- meaning
- emotional arc
- character/identity/wardrobe/location/cultural locks
- shot graph
- visual grammar references
- captions
- lip-sync
- editing
- renderers
- QC
- defects
- repairs
- approvals
- final state

## Pixelle Audit

Created:

- `director-os-research/PIXELLE_VIDEO_CODE_AUDIT.md`
- `director-os-research/PIXELLE_ADOPTION_MAP.json`
- `director-os-research/PIXELLE_LICENSE_NOTICE.md`

Actual finding:

- No official Pixelle-Video repository could be verified/cloned anonymously in this environment.
- No Pixelle code was copied.
- Director OS adapted workflow patterns only: atomic capabilities, workflow providers, one-topic UX, task history, concurrency/iteration control, output storage, and repair loop patterns.

## Focal Benchmark

Created:

- `director-os-research/FOCAL_PRODUCT_BENCHMARK.md`

Implemented benchmark behaviours:

- one-prompt creation
- generated production graph
- timeline preview
- generation history / loop history
- defect and repair history
- consolidated approval flow

Still missing:

- real AI image/video generation
- conversational whole-project editing
- provider-backed shot replacement
- local ASR lyric matching

## Acceptance Run

Command run:

```bash
tools/director-os studio-create "<full Burmese music video acceptance brief>" --project /Users/chan/song-video-project
```

Created loop:

- loop ID: `1`
- final status: `awaiting_approval`
- current iteration: `2`
- quality score: `57.53`
- URL: `http://127.0.0.1:8787/studio-loop/1`

Artifacts:

- `director-os/evaluations/1/EVALUATION.json`
- `director-os/evaluations/1/DEFECTS.json`
- `director-os/evaluations/1/REPAIRS.json`
- `director-os/evaluations/1/FINAL_ACCEPTANCE.json`
- `director-os/evaluations/1/STUDIO_LOOP_REPORT.md`

## Output Evaluated

The loop evaluated actual Run 15 media:

- clean MP4 duration: `292.657007s`
- captioned MP4 duration: `292.657007s`
- master duration: `292.702041s`
- duration status: `ok`
- resolution: `1920x1080`
- video codec: `h264`
- audio codec: `aac`

## Defects Found

Detected defects:

- `CAPTION_SYNC_UNVERIFIED`
- `LIPSYNC_PROVIDER_UNAVAILABLE`
- `LOCAL_ASR_UNAVAILABLE`
- `AI_GENERATION_UNAVAILABLE`

Critical failure:

- `CAPTION_SYNC_UNVERIFIED`

The loop did not claim final acceptance.

## Repairs Performed

Safe repair path:

- regenerated sync calibration candidates
- rebuilt v6 captions
- rebuilt Run 15 sync-calibrated review animatic
- re-evaluated actual MP4 output

Repairs requiring approval:

- local ASR setup or manual listening approval for trusted lyric timing
- local storyboard/image model setup for real AI-generated frames
- lip-sync provider setup only after sync and shot eligibility improve

## Acceptance Result

Acceptance did not pass.

Final status:

- `awaiting_approval`

Consolidated approval required:

- choose one local storyboard/ASR capability before final AI generation or trusted lyric alignment can pass

This is the correct stop condition because local-safe deterministic repairs cannot produce real AI frames or ASR-verified Burmese lyric timing.

## Tests

Passed:

- `python3 -m py_compile $(find director-os-web/app director-os-web/scripts -name '*.py' -print | sort)`
- `cd director-os-web && python3 scripts/smoke_test_local.py`
- live HTTP check: `/studio-loop` returned `200`
- live HTTP check: `/studio-loop/1` returned `200`
- live HTTP check: `/studio-loop/1/evaluation` returned `200`
- live HTTP check: `/director-assets/animatics/15/ANIMATIC_WITH_CAPTIONS_SYNC_CALIBRATED_REVIEW.mp4` returned `200 video/mp4`
- studio loop CLI run
- studio loop CLI status/evaluation/report

Smoke-test output:

```text
smoke ok
test_database: /Users/chan/song-video-project/director-os-web/data/director_os_test.sqlite
dry_run_job: 1
manual_export: 1
kling_manual_export: 2
result_id: 1
result_dir: /Users/chan/song-video-project/director-os-web/result-media-test/burmese-music-video/F01_side_travel_dance/1
```

## Live App

The updated app server was restarted at:

- `http://127.0.0.1:8787`

Primary loop page:

- `http://127.0.0.1:8787/studio-loop/1`

## Next Action

Open:

- `http://127.0.0.1:8787/studio-loop/1`

Then choose the next consolidated approval:

1. approve local ASR setup for stronger Burmese lyric alignment, or
2. approve local storyboard/image generation setup for real AI frames, or
3. continue manual listening review and composite-only planning without calling the project production-ready.
