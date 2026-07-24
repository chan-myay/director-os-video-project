# Director OS v1.0.5 Emergency Sync and Route Repair Report

## Route Repair

- `/animatic` direct route validation: `200`
- Old Run 11 media route: `200 video/mp4` when file exists
- Latest Run 13 captioned review media route: `200 video/mp4`
- Path traversal: `403`
- Missing animatic media: useful `404` HTML response

Audit:

- `director-os-web/V1_0_5_INTERNAL_SERVER_ERROR_AUDIT.md`

The first curl reproduction in this session found the local server unreachable rather than returning a stack trace. A stale process on port `8787` was terminated and the app was restarted. The route itself is now defensive against missing latest-run pointers, missing status files, missing MP4s, old defective runs, and missing caption/font/sync data.

## Latest Safe Animatic

- Latest safe version: `13`
- Run 13 folder: `director-os/animatics/13/`
- Clean MP4: `director-os/animatics/13/ANIMATIC.mp4`
- Captioned review MP4: `director-os/animatics/13/ANIMATIC_WITH_CAPTIONS_REVIEW.mp4`
- Review MP4: `director-os/animatics/13/ANIMATIC_REVIEW.mp4`

Duration:

- Master duration: `292.702041` seconds
- Run 13 duration: `292.657007` seconds
- Difference: `0.045034` seconds
- Validation: `ok`
- Cutoff fixed: `yes`

Run 11 remains preserved and superseded:

- `director-os/animatics/11/SUPERSEDED_STATUS.json`

## Auto Lyric Sync

Generated:

- `director-os/state/AUTO_LYRIC_SYNC.json`

Method:

- `level_b_existing_vocal_boundary_plus_phrase_order`

Counts:

- Auto-synced phrase suggestions: `17`
- Low-confidence phrase suggestions: `17`
- Blocked phrase count from wrong-line markers: `0`
- Local ASR used: `no`
- Local ASR available: `false`

Important honesty label:

- `auto_boundary_unverified`

This is not word-level, syllable-level, phoneme-level, ASR-verified, or human-listening verified alignment. It is the strongest local automatic sync currently available without downloading an ASR model or calling cloud APIs.

## Caption v4

Generated:

- `director-os/captions/final-timing-v4/CAPTIONS_REVIEW_AUTO.srt`
- `director-os/captions/final-timing-v4/CAPTIONS_REVIEW_AUTO.vtt`
- `director-os/captions/final-timing-v4/CAPTIONS_REVIEW_AUTO.ass`
- `director-os/captions/final-timing-v4/AUTO_SYNC_STATUS.json`
- `director-os/captions/final-timing-v4/CAPTION_BLOCKERS.json`
- `director-os/captions/final-timing-v4/FONT_STATUS.json`

Production caption files were not generated because production captions are blocked by:

- low-confidence automatic sync
- listening review not completed
- Unicode approval still required

Review captions visibly include:

- phrase ID
- `AUTO_BOUNDARY_UNVERIFIED`
- confidence score
- lyric text

They do not appear during instrumental gaps outside the 17 phrase regions.

## Burmese Font Hardening

Selected font:

- `Noto Sans Myanmar`

Generated preview:

- `director-os/captions/font-preview/FONT_SAMPLE.png`
- `director-os/captions/font-preview/CAPTION_OVERLAY_SAMPLE.png`
- `director-os/captions/font-preview/FONT_RENDER_STATUS.json`

Render result:

- Font readable: `true`
- Render test passed: `true`
- Style: large 1080p caption text, high contrast, outline/black box, safe lower margin

## Music Analysis

Generated/updated:

- `director-os/state/MUSIC_ANALYSIS.json`

Visible route:

- `/music-analysis`

Includes:

- master duration
- RMS energy curve
- vocal phrase regions
- instrumental gaps
- intro/outro candidates
- energy peaks
- warning that this is not word/phoneme recognition

## Voice and Lip-Sync Honesty

Voice sync:

- `not_tested_no_voice_audio`

Lip-sync readiness:

- `blocked_on_auto_sync_low_confidence`

Readiness reasons:

- `blocked_on_auto_sync_low_confidence`
- `blocked_on_listening_review`
- `blocked_on_unicode_review`

InfiniteTalk/lip-sync packaging remains blocked until timing and Unicode are reviewed and source shot eligibility is satisfied.

## UI Added Or Updated

- `/animatic`
- `/auto-sync`
- `/music-analysis`
- `/burmese-language/listening-sync`
- `/burmese-language/font-check`
- `/captions-voice/sync`
- Command Center

The Command Center now points to auto lyric sync review instead of implying captions or lip-sync are ready.

## CLI Added Or Updated

Validated:

- `tools/director-os diagnose-route /animatic`
- `tools/director-os animatic-audit /Users/chan/song-video-project`
- `tools/director-os auto-sync-lyrics /Users/chan/song-video-project`
- `tools/director-os auto-sync-status /Users/chan/song-video-project`
- `tools/director-os rebuild-captions /Users/chan/song-video-project --version v4 --auto-sync`
- `tools/director-os rebuild-animatic /Users/chan/song-video-project --version 13 --full-song --review-captions`
- `tools/director-os font-check /Users/chan/song-video-project`
- `tools/director-os music-analysis /Users/chan/song-video-project`
- `tools/director-os caption-readiness /Users/chan/song-video-project`
- `tools/director-os lipsync-readiness /Users/chan/song-video-project`

## Tests

Passed:

- `python3 -m py_compile $(find director-os-web/app director-os-web/scripts -name '*.py' -print | sort)`
- `cd director-os-web && python3 scripts/smoke_test_local.py`

Smoke test now includes v1.0.5 checks for:

- safe animatic resolver
- old Run 11 media behavior
- missing-media behavior
- path traversal blocking
- auto-sync generation
- low-confidence sync blocking
- font preview rendering
- caption v4 review/blocking

No model download, paid API call, upload, or source overwrite occurred.

## Exact Next User Action

Open:

- `http://127.0.0.1:8787/animatic`

Then:

1. Open `Auto Sync`.
2. Review the 17 phrase suggestions.
3. Use `Listening Review` to play each phrase and approve or correct it.

Do not treat captions or lip-sync as production-ready until those review decisions are saved.
