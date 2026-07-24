# Director OS v2.1 One-Screen Automatic Studio Report

## Summary

Director OS v2.1 adds the visible one-screen Studio workflow:

UPLOAD
→ WRITE ONE IDEA
→ CREATE EVERYTHING
→ WATCH LOCAL VIDEO SKETCH
→ REFINE WITH ONE SENTENCE
→ EXPORT OR BEGIN PRODUCTION

This build preserves v0.1-v2.0 infrastructure, Runs 9-15, Studio Loop 1, existing project evidence, Burmese language state, captions, animatics, privacy/spend gates, renderer planning, lip-sync planning, jobs, exports, QC and audit history.

No paid API call, private media upload, substantial model download, storyboard model install, voice model install, InfiniteTalk install or destructive source-media operation was performed.

## Studio Routes

Implemented:

- `/studio`
- `/studio/projects/new`
- `/studio/projects/{project_id}`
- `/studio/projects/{project_id}/upload`
- `/studio/projects/{project_id}/create`
- `/studio/projects/{project_id}/continue`
- `/studio/projects/{project_id}/progress`
- `/studio/projects/{project_id}/result`
- `/studio/projects/{project_id}/storyboard`
- `/studio-assets/{project_id}/{asset_path}`

Root route:

- `/` redirects to `/studio`

The previous Command Center remains available at:

- `/command-center`

## Upload Capability

Implemented managed local uploads under:

- `director-os/projects/<project_id>/inputs/`
- `director-os/projects/<project_id>/thumbnails/`
- `director-os/projects/<project_id>/contact-sheets/`
- `director-os/projects/<project_id>/waveforms/`

Supported extensions:

- JPG, JPEG, PNG, HEIC, WebP
- MP4, MOV, WebM
- MP3, WAV, M4A, FLAC
- TXT, SRT, VTT, ASS
- PDF

For every uploaded input Director OS:

- sanitizes filename
- blocks path traversal by writing only into managed project storage
- computes SHA-256
- deduplicates by hash
- detects media type
- classifies likely role
- records privacy/rights state
- probes dimensions/duration where applicable
- attempts thumbnail/contact-sheet/waveform generation for media types

The upload route works without `python-multipart`; v2.1 added a small local multipart parser because the deployed app environment did not include that package.

Manual upload validation:

- Uploaded existing local lyric file: `lyrics/အခ်စ္မဲ့ ဇာတ္လမ္း - Zawgyi.txt`
- Stored copy: `director-os/projects/burmese-music-video/inputs/51b07bfca4c4-Zawgyi.txt`
- Classification: `lyrics`
- Source file was not modified.

## Project Scan Results

Project:

- `burmese-music-video`

Created/updated:

- `director-os/projects/burmese-music-video/PROJECT.json`
- `director-os/projects/burmese-music-video/INPUTS.json`
- `director-os/projects/burmese-music-video/SCAN_SUMMARY.json`

Director OS found and preserved:

- approved A1/A2 performer face references
- approved body/wardrobe reference B
- approved bar/stage reference C
- approved Burmese art-world reference E
- `audio/01.mp3` master song
- existing Burmese lyric/caption state
- existing storyboard and visual grammar records
- existing failure and privacy memory
- rejected/restricted identity material remains blocked

Current managed uploaded input count:

- `1`

Input classifications:

- lyrics: `1`

## Concepts Created

Created:

- `director-os/projects/burmese-music-video/CONCEPTS.json`

Concept count:

- `3`

Recommended concept:

- `The Bar Remembers Her`

Other concepts:

- `Winter Window, Crimson Dress`
- `Objects After Love`

Each concept includes:

- title
- one-sentence idea
- palette
- setting
- performance approach
- camera approach
- movement approach
- edit rhythm
- strengths
- risks

## Storyboard Status

Created:

- `director-os/projects/burmese-music-video/STORYBOARD.json`

Shot count:

- `24`

Storyboard UI:

- `/studio/projects/burmese-music-video/storyboard`

Each card shows:

- frame image
- shot ID
- timecode
- story purpose
- camera
- lighting
- performer movement
- renderer
- fallback renderer
- quality status
- origin label

Advanced controls are represented as collapsed/low-emphasis actions:

- approve
- reject
- refine
- regenerate this shot

## Visual Generation Status

Real AI-generated frame count:

- `0`

Composite frame count:

- `24`

All storyboard frames are labelled:

- `LOCAL ASSET COMPOSITE`

No deterministic composite was called AI-generated.

Remaining optional approval:

- local storyboard/image model setup for real AI frames

## Video Sketch

Created:

- `director-os/projects/burmese-music-video/previews/CREATIVE_SKETCH.mp4`
- `director-os/projects/burmese-music-video/previews/CREATIVE_SKETCH_WITH_CAPTIONS.mp4`
- `director-os/projects/burmese-music-video/previews/CREATIVE_SKETCH_REVIEW.mp4`
- `director-os/projects/burmese-music-video/previews/VIDEO_SKETCH_STATUS.json`

Label:

- `LOCAL PREVIS VIDEO SKETCH - NOT FINAL VIDEO`

Source:

- Run 15 full-song local animatic

Validated MP4 metadata:

- duration: `292.657007s`
- resolution: `1920x1080`
- video codec: `h264`
- audio codec: `aac`
- streams: `2`

No song cutoff was detected in the reused Run 15 sketch.

## Captions Status

Caption output used:

- v6 sync-calibrated review captions

Status:

- review-only / not production-ready

Reason:

- Burmese lyric timing still lacks human-approved or ASR-supported confidence.

Director OS continues to label caption sync honestly and does not mark captions final.

## Lighting, Camera And Blocking

Included automatically in the Studio storyboard and prompt package:

- camera movement
- lighting direction
- blocking/performance movement
- composition/diagram references
- renderer and fallback renderer

The primary Studio view shows concise shot direction. Full details remain available through existing storyboard/shot-plan/advanced systems.

## Prompt Packages

Created:

- `director-os/projects/burmese-music-video/production-packages/PACKAGE_MANIFEST.json`
- one package per shot under `director-os/projects/burmese-music-video/production-packages/`

Prompt package count:

- `24`

Each package includes:

- short director instruction
- full technical prompt
- negative prompt
- input-reference mapping
- motion mapping
- identity rules
- body rules
- privacy state
- likely failures
- QC scorecard

The result page exposes:

- `EXPORT PRODUCTION PACKAGE`

## Studio Loop Iterations

The one-screen CREATE EVERYTHING workflow created:

- Studio Loop `2`

Loop status:

- `awaiting_approval`

Iterations:

- `2`

Quality score:

- `57.53`

Loop URL:

- `http://127.0.0.1:8787/studio-loop/2`

## Defects Found

Studio Loop 2 detected:

- `CAPTION_SYNC_UNVERIFIED`
- `LIPSYNC_PROVIDER_UNAVAILABLE`
- `LOCAL_ASR_UNAVAILABLE`
- `AI_GENERATION_UNAVAILABLE`

Critical defect:

- `CAPTION_SYNC_UNVERIFIED`

Director OS did not claim final acceptance.

## Repairs Performed

Safe local repair path:

- reused calibrated brain timeline
- rebuilt/reused v6 caption path
- built project-local full-song MP4 sketch files
- evaluated actual MP4 output
- preserved approval gates for ASR/model/lip-sync work

No paid retry or cloud-dependent repair was attempted.

## Local Capabilities Used

Used:

- Python local services
- SQLite-backed existing state
- local FFmpeg/FFprobe
- existing local composite previs
- existing full-song Run 15 animatic
- existing Burmese caption pipeline
- existing Studio Loop evaluator

Not used:

- paid APIs
- cloud upload
- local storyboard model
- voice provider
- InfiniteTalk
- local ASR model

## Optional Approvals Remaining

The next consolidated approval remains:

- choose local ASR setup for stronger Burmese lyric alignment, or
- choose local storyboard/image model setup for real AI frames, or
- continue manual listening review and composite-only planning

Voice and InfiniteTalk remain optional and blocked until prerequisite sync/provider approvals exist.

## Route Validation

Live route checks:

- `/studio` returned `200`
- `/studio/projects/burmese-music-video` returned `200`
- `/studio/projects/burmese-music-video/result` returned `200`
- `/studio/projects/burmese-music-video/storyboard` returned `200`
- `/studio-assets/burmese-music-video/previews/CREATIVE_SKETCH_WITH_CAPTIONS.mp4` returned `200 video/mp4`
- `/` returns `307` redirect to `/studio`
- `/command-center` returned `200`

Upload route validation:

- POST `/studio/projects/burmese-music-video/upload` returned `303`

## Tests

Passed:

- `python3 -m py_compile $(find director-os-web/app director-os-web/scripts -name '*.py' -print | sort)`
- `cd director-os-web && python3 scripts/smoke_test_local.py`

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

## Exact Next Action

Open:

- `http://127.0.0.1:8787/studio`

Review:

- `http://127.0.0.1:8787/studio/projects/burmese-music-video/result`

Then choose one consolidated next step:

1. approve local ASR setup to improve Burmese lyric timing,
2. approve local storyboard/image generation setup for real AI frames, or
3. continue manual listening review while using composite previews.
