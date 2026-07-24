# Director OS v0.9 One-Command AI Studio Report

## Real Intelligence Provider Status

Implemented provider layer:

- `app/intelligence/provider.py`
- `codex_provider.py`
- `fallback_provider.py`
- `mock_provider.py`
- `schemas.py`
- `context_builder.py`
- `response_validator.py`
- `provider_health.py`
- `run_security.py`

The installed Codex CLI was inspected:

- path: `/Users/chan/.local/bin/codex`
- version observed: `codex-cli 0.142.5`
- supported non-interactive command: `codex exec`

Validated one real Codex provider stage outside the tool sandbox. It returned
structured JSON for `project_archaeology` and passed validation.

Automated tests use `MockProvider` only.

## Autonomous Stages Completed

Implemented and persisted 17 stages:

1. `project_archaeology`
2. `music_analysis`
3. `burmese_language_analysis`
4. `public_research`
5. `concept_development`
6. `concept_selection`
7. `character_and_performance`
8. `environment_and_production_design`
9. `composition_and_blocking`
10. `lighting_and_cinematography`
11. `movement_direction`
12. `storyboard_generation`
13. `caption_and_voice_plan`
14. `edit_and_animatic`
15. `renderer_strategy`
16. `production_preparation`
17. `ready_for_review`

Created routes:

- `/director-runs`
- `/director-runs/new`
- `/director-runs/{run_id}`
- `/director-runs/{run_id}/events`
- `/director-runs/{run_id}/pause`
- `/director-runs/{run_id}/resume`
- `/director-runs/{run_id}/cancel`
- `/director-runs/{run_id}/retry/{stage}`
- `/director-runs/{run_id}/questions`
- `/settings/intelligence`

Run #1 completed all 17 stages locally and stopped with honest blockers.

## Project Evidence Reused

The v0.9 run reuses:

- canonical state in `director-os/state/`
- approved/rejected reference decisions
- success/failure memory
- song energy analysis
- selected/rejected footage labels
- v0.8 storyboard workspace
- v0.6 production-control/QC infrastructure
- Burmese project locks and hard negatives

## Research Sources Found

Stored 20 public research lead records in `research_items`.

Categories include:

- restrained female performance
- intimate bar cinematography
- lateral performer movement
- Burmese lacquer/textile/craft material references
- mature blues/jazz edit rhythm

Rights handling:

- link-only
- do not copy/rehost
- verification status recorded in notes

## Concepts Generated

The existing v0.7/v0.8 concept engine remains active and selected:

- `The Bar Remembers Her`

The v0.9 staged system persists concept stages and can retry/regenerate stages.
Full multi-concept Codex expansion is available through the real provider but
was not run for all 17 stages during automated validation.

## Storyboard And Visual Grammar Status

Storyboard:

- 24 persistent storyboard cards
- decisions/comments/versioning preserved
- route: `/storyboard`

Visual grammar:

- 24 `visual_grammar` rows
- machine-readable composition, camera, lighting and blocking
- 24 blocking diagram SVG files in `director-os/diagrams/latest/`

## Local AI Image Backend Status

Current status:

- `LOCAL STORYBOARD MODEL REQUIRED`

No local AI image model is installed or marked healthy.
No model weights were downloaded.
No AI-generated images were claimed.

Recommended next decision must be consolidated around one local storyboard model
or an approved cloud image provider.

## Image Counts

- genuinely AI-generated images: `0`
- asset/composite PNG previs images: `24` primary frames
- additional composite previs options: `18`
- blocking diagrams: `24`

Composite images are labeled as composite/fallback, not AI generation.

## Movement-Director Status

Created:

- `director-os/plans/latest/PHONE_RECORDABLE_MOVEMENT_BRIEFS.md`

Movement-heavy shots receive phone-recordable mechanics including:

- grounded lateral steps
- weight transfer
- arm level below shoulder
- shoulder/torso rhythm
- head direction
- camera position
- floor marks
- explicit hard negatives

Motion video analysis remains metadata/rule based until a richer local vision
backend is approved.

## Burmese Language Status

Implemented:

- original lyric preservation
- editable normalized/caption text
- pronunciation-helper fields
- caption timing/status fields
- JSON/CSV caption workspace

Exports:

- `director-os/captions/latest/CAPTIONS.srt`
- `director-os/captions/latest/CAPTIONS.vtt`
- `director-os/captions/latest/CAPTIONS.ass`

Full Zawgyi-to-Unicode conversion remains conservative/incomplete.

## Voice Provider Status

Voice provider framework status file:

- `director-os/voice/VOICE_PROVIDER_STATUS.json`

Actual generated voice samples:

- `0`

Reason:

- no approved/configured Burmese-capable provider
- no cloud voice approval
- no real-person voice-cloning consent workflow completed

Blocker:

- `VOICE_PROVIDER_NOT_CONFIGURED`

## MP4 Animatic Status

HTML animatic remains available:

- `director-os/animatics/latest/ANIMATIC.html`

Edit handoff files were created for run #1:

- `director-os/animatics/1/TIMELINE.otio`
- `director-os/animatics/1/TIMELINE.edl`
- `director-os/animatics/1/DAVINCI_HANDOFF.xml`
- `director-os/animatics/1/SHOT_LIST.csv`
- `director-os/animatics/1/EDIT_DECISIONS.json`
- `director-os/animatics/1/BUILD_LOG.txt`

MP4 animatic:

- not created

Reason:

- no `ffmpeg` executable was discoverable on the current shell path

Blocker:

- `FFMPEG_REQUIRED_FOR_MP4_ANIMATIC`

## Renderer Strategy Status

Renderer strategy remains per-shot and differentiated:

- Seedance for side-travel/body motion where approved motion reference exists
- Kling Motion Control where character/start-frame and motion video exist
- existing footage for selected object/story shots
- local composite/storyboard fallback
- manual/export gates still required before cloud tests

Identical generic renderer packages are not used for production readiness.

## CLI Status

Implemented:

```bash
tools/director-os create "<idea>" --project /Users/chan/song-video-project
tools/director-os continue /Users/chan/song-video-project
tools/director-os status /Users/chan/song-video-project
tools/director-os status /Users/chan/song-video-project --json
tools/director-os concepts /Users/chan/song-video-project
tools/director-os storyboard /Users/chan/song-video-project
tools/director-os build-animatic /Users/chan/song-video-project
tools/director-os voice-test /Users/chan/song-video-project
tools/director-os produce /Users/chan/song-video-project --dry-run
tools/director-os sync-workspace /Users/chan/song-video-project
tools/director-os review-status /Users/chan/song-video-project
```

`status` prints run ID, current stage, completed/total stages, last artifact,
blockers, decisions required, next action and web URL.

## Tests

Commands run:

```bash
python3 -m py_compile $(find director-os-web/app director-os-web/scripts -name '*.py' -print | sort)
cd director-os-web && python3 scripts/smoke_test_local.py
```

Smoke test uses:

- isolated SQLite DB
- isolated result media root
- mock intelligence provider
- network disabled
- synthetic media
- no private project asset upload
- no external API
- no model downloads

It verifies:

- provider invocation through mock
- stage persistence
- all 17 stages
- research records
- visual grammar records
- storyboard versioning/comments
- Burmese caption workspace
- voice-test records
- existing job/export/result/QC flow
- no dev DB mutation

## Preserved Old Infrastructure

Preserved:

- Command Center
- Director Plan
- Storyboard
- Shot Plan
- Production
- Research Assistant
- Advanced production controls
- asset registry
- canonical state
- shot packs
- jobs
- exports
- result import
- QC
- audit history
- v0.8 storyboard decisions/comments/previs/animatic records

## Exact Blockers

The current v0.9 real-project run is blocked by:

- `FFMPEG_REQUIRED_FOR_MP4_ANIMATIC`
- `LOCAL_STORYBOARD_MODEL_REQUIRED`
- `VOICE_PROVIDER_NOT_CONFIGURED`

No paid API call, personal-media upload, model download, final render
submission, publishing, deletion or destructive change occurred.

## Next Production Action

One consolidated approval decision is needed:

1. Provide or install `ffmpeg` for MP4 animatic export.
2. Approve one local storyboard image model, or explicitly approve a cloud image
   provider with spend/upload limits.
3. Configure one Burmese-capable voice provider, or keep voice testing manual.

The safest immediate next production step is to resolve `ffmpeg` first, because
it enables MP4 animatics without cloud upload or private-media exposure.
