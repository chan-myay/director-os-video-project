# Director OS v0.9.1 Operational Unblock Report

## Summary

v0.9.1 corrected the false hard-block state, discovered the existing local FFmpeg/FFprobe binaries, generated the first real local MP4 animatic, added consolidated setup pages, and made CLI/UI status separate hard blockers from approvals, optional capabilities, and warnings.

Latest operational run:

- Run: 9
- Status: ready_with_approvals
- Stages: 17/17 completed
- Hard blockers: none
- Next action: Review the MP4 animatic and decide whether to configure AI storyboard generation.

## Original Blockers and Corrected Severity

| Blocker | Corrected status | Notes |
|---|---|---|
| FFMPEG_REQUIRED_FOR_MP4_ANIMATIC | resolved / hard_blocker only if genuinely absent | FFmpeg and FFprobe were found and verified locally. |
| LOCAL_STORYBOARD_MODEL_REQUIRED | approval_required | Blocks real AI storyboard generation only. Does not block director plan, composite previs, captions, animatic, or production planning. |
| VOICE_PROVIDER_NOT_CONFIGURED | optional_capability | Blocks generated voice samples only. Does not block caption planning, storyboard, animatic, or renderer planning. |
| CODEX_PROVIDER_USAGE_LIMIT | warning | Blocks the full real Codex-provider acceptance run until quota resets or credits are available. Does not block the local director package. |

## FFmpeg Discovery Result

FFmpeg and FFprobe are available without installing anything:

- FFmpeg: `/Users/chan/song-video-project/local-tools/envs/faceswap/bin/ffmpeg`
- FFmpeg version: `ffmpeg version 6.0-tessus`
- FFprobe: `/Users/chan/song-video-project/local-tools/envs/faceswap/bin/ffprobe`
- FFprobe version: `ffprobe version 6.0-tessus`

`director-os-web/scripts/run_local.sh` now exports a safe PATH including the project local FFmpeg path and common Homebrew locations.

## MP4 Animatic Generated

Generated files:

- `director-os/animatics/9/ANIMATIC.mp4`
- `director-os/animatics/9/ANIMATIC_WITH_CAPTIONS.mp4`
- `director-os/animatics/9/ANIMATIC_REVIEW.mp4`
- `director-os/animatics/9/BUILD_LOG.txt`
- `director-os/animatics/9/FFMPEG_COMMAND.json`
- `director-os/animatics/9/MEDIA_METADATA.json`
- `director-os/animatics/9/TIMELINE.otio`
- `director-os/animatics/9/TIMELINE.edl`
- `director-os/animatics/9/DAVINCI_HANDOFF.xml`
- `director-os/animatics/9/SHOT_LIST.csv`

Validated metadata:

- Duration: 193.76 seconds
- Resolution: 1920x1080
- Video codec: h264
- Audio codec: aac
- Streams: 2
- Clean MP4 size: 5,476,266 bytes
- Captioned MP4 size: 5,869,944 bytes
- Review MP4 size: 5,513,038 bytes

The `/animatic` page now plays the actual run 9 MP4 and links the clean, captioned, and review versions.

## Real Codex Provider Status

Provider:

- `codex_cli`
- Version: `codex-cli 0.142.5`

What passed:

- A real Codex structured-stage test completed successfully for `project_archaeology`.
- The provider now uses `--output-schema` and `--output-last-message` where available.
- The response parser now handles mixed output safely and preserves provider stage mismatch evidence.

What blocked the full real-provider run:

- The local Codex account hit a usage limit during the full 17-stage acceptance attempt.
- The run retried provider calls and then used explicit local fallback per stage.
- Fallback was not silent: every fallback stage is recorded as `PROVIDER_FALLBACK_USED:<stage>`.

Run 9 result:

- 17/17 stages completed.
- Status: `ready_with_approvals`.
- Warning: `CODEX_PROVIDER_USAGE_LIMIT`.
- No paid API calls, uploads, or model downloads occurred.

## Research Verification

Stored research records now include:

- `verification_status`
- `source_domain`
- `retrieval_date`
- `what_not_to_copy`

Current count:

- `search_suggestion_only`: 60

Because the provider quota blocked the real research stage, these are link/search leads rather than a completed provider-synthesized research board. They are rights-aware and marked link-only/do-not-copy.

## Setup Decisions

Added:

- `/setup/storyboard-model`
- `/setup/burmese-voice`
- `setup_decisions` table

Storyboard model page shows:

- One primary local option
- One lighter/composite fallback
- One cloud option
- Exact approval choices
- No automatic model installation

Burmese voice page shows:

- System voice detection
- Caption-only recommendation
- Manual human voice fallback
- Cloud/provider setup remains explicit
- No cloud voice call
- No voice cloning

## CLI Status

Command:

```bash
tools/director-os status /Users/chan/song-video-project
```

Result:

```text
run_id: 9
status: ready_with_approvals
completed_stages: 17/17
hard_blockers:
- none
approvals_needed:
- LOCAL_STORYBOARD_MODEL_REQUIRED
optional_capabilities:
- VOICE_PROVIDER_NOT_CONFIGURED
warnings:
- PROVIDER_FALLBACK_USED:project_archaeology
- CODEX_PROVIDER_USAGE_LIMIT
...
created:
- director treatment
- 24-shot storyboard
- 24 visual grammar records
- 24 blocking diagrams
- MP4 animatic
- caption exports
- renderer strategy
next_action: Review the MP4 animatic and choose whether to configure AI storyboard generation.
web_url: http://127.0.0.1:8787/director-runs/9
```

Exit code:

- `0` for `ready` and `ready_with_approvals`

## Routes Verified

Verified on the restarted local server:

- `/` -> 200
- `/animatic` -> 200
- `/settings/system-tools` -> 200
- `/setup/storyboard-model` -> 200
- `/setup/burmese-voice` -> 200
- `/director-runs/9` -> 200
- `/director-assets/animatics/9/ANIMATIC.mp4` -> 200, 5,476,266 bytes

Local server:

- `http://127.0.0.1:8787`

## Tests

Passed:

```bash
python3 -m py_compile $(find director-os-web/app director-os-web/scripts -name '*.py' -print | sort)
cd director-os-web
python3 scripts/smoke_test_local.py
tools/director-os status /Users/chan/song-video-project
tools/director-os status /Users/chan/song-video-project --json
```

Smoke test validated:

- isolated test database
- blocker severity grouping
- `ready_with_approvals`
- optional voice not blocking
- optional image model not blocking
- FFmpeg/FFprobe health
- MP4 animatic creation from synthetic/test-safe path
- ffprobe metadata validation
- setup decision persistence
- no API call
- no upload
- no model download
- no normal development database mutation

## No-Spend / No-Upload / No-Download Confirmation

Confirmed:

- No paid API call
- No third-party media upload
- No model-weight download
- No source media overwrite
- No private reference folder copied into export output
- No real renderer submission
- No real voice provider call

## Files and Services Added or Updated

Added:

- `director-os-web/app/system_tools/binary_discovery.py`
- `director-os-web/app/system_tools/ffmpeg_service.py`
- `director-os-web/app/system_tools/tool_health.py`
- `director-os-web/app/services/blocker_service.py`
- `director-os-web/app/services/setup_decision_service.py`
- `director-os-web/app/templates/system_tools.html`
- `director-os-web/app/templates/setup_storyboard_model.html`
- `director-os-web/app/templates/setup_burmese_voice.html`

Updated:

- `director-os-web/app/intelligence/codex_provider.py`
- `director-os-web/app/intelligence/response_validator.py`
- `director-os-web/app/intelligence/run_security.py`
- `director-os-web/app/services/db.py`
- `director-os-web/app/services/v09_studio_service.py`
- `director-os-web/app/main.py`
- `director-os-web/app/templates/command_center.html`
- `director-os-web/app/templates/animatic.html`
- `director-os-web/scripts/run_local.sh`
- `director-os-web/scripts/smoke_test_local.py`
- `tools/director-os`

## Exact Next User Action

Open:

```text
http://127.0.0.1:8787/animatic
```

Review:

- Clean MP4 animatic
- Captioned MP4 animatic
- Review MP4 animatic

Then choose one:

- Continue with composite previs for now
- Approve a local storyboard model setup
- Decide later

The production plan is no longer falsely hard-blocked.
