# Director OS v1.0.7 Sync Calibration And Run 15 Report

## Purpose

v1.0.7 adds a smart lyric-sync calibration loop on top of the v1.0.6 production brain timeline. It does not claim production sync, lyric recognition, word alignment, phoneme alignment, or lip-sync readiness.

No storyboard model, voice model, InfiniteTalk model, paid API, cloud upload, or source-media overwrite was performed. Runs 9, 11, 12, 13, and 14 were preserved.

## Run 14 Status

- Run 14 exists and remains preserved.
- Run 14 duration: `292.657007s`
- Master duration: `292.702041s`
- Difference: `0.045034s`
- Status: full-song OK
- Run 14 offset: `+0.405s`
- Run 14 sync method: `boundary_plus_global_offset`
- Run 14 remained low-confidence and not production-ready.

## Offset Candidates

Created:

- `director-os/state/SYNC_OFFSET_CANDIDATES.json`

Candidate offsets:

- `+0.180s`
- `+0.405s`
- `+0.600s`
- `+0.800s`
- `+1.000s`
- `+1.200s`

Selected review candidate:

- `+0.800s`

Reason:

- fewer captions start before detected vocal onset

Important limitation:

- This is waveform/onset-supported calibration, not ASR, word alignment, syllable alignment, or phoneme alignment.

## Feedback State

Created/updated:

- `director-os/state/SYNC_FEEDBACK.json`

Current feedback:

- user-approved global offset: none
- feedback events: 0
- proposed next action: approve proposed global offset or adjust from the sync calibration page

The UI can now store:

- global early/late corrections
- phrase-level status
- wrong-line markers
- approved global offset

## ASR Availability

Created/updated:

- `director-os/state/LOCAL_ASR_ALIGNMENT.json`

Detected ASR status:

- `mlx_whisper`: unavailable
- `whisper_cli`: unavailable
- `whisper_cpp`: unavailable
- Burmese verified: false
- local ASR classification: `asr_unavailable`

No model was downloaded. `/setup/local-asr` now shows the local/private ASR decision path.

## Brain Timeline Update

Updated:

- `director-os/state/PRODUCTION_BRAIN_TIMELINE.json`

Each phrase now includes:

- original boundary timing
- Run 14 corrected timing
- candidate corrected timing
- user-approved timing slot
- ASR timing slot
- final review timing
- sync method
- confidence
- feedback count
- production-ready flag

Current sync method counts:

- `vocal_onset_corrected`: 17

Confidence counts:

- high: 0
- medium: 15
- low: 2

All 17 phrases still have production blockers because no timing has been human-approved or ASR-verified.

## Captions v6

Created:

- `director-os/captions/final-timing-v6/CAPTIONS_REVIEW_SYNC_CALIBRATED.srt`
- `director-os/captions/final-timing-v6/CAPTIONS_REVIEW_SYNC_CALIBRATED.vtt`
- `director-os/captions/final-timing-v6/CAPTIONS_REVIEW_SYNC_CALIBRATED.ass`
- `director-os/captions/final-timing-v6/SYNC_FEEDBACK_SUMMARY.json`
- `director-os/captions/final-timing-v6/OFFSET_CANDIDATES.json`
- `director-os/captions/final-timing-v6/CAPTION_BLOCKERS.json`

Production captions remain blocked by:

- sync calibration not human-approved
- Unicode review still required for production

## Run 15

Created:

- `director-os/animatics/15/ANIMATIC.mp4`
- `director-os/animatics/15/ANIMATIC_WITH_CAPTIONS_SYNC_CALIBRATED_REVIEW.mp4`
- `director-os/animatics/15/ANIMATIC_REVIEW.mp4`
- `director-os/animatics/15/DURATION_VALIDATION.json`
- `director-os/animatics/15/SYNC_FEEDBACK_SUMMARY.json`
- `director-os/animatics/15/OFFSET_CANDIDATES.json`
- `director-os/animatics/15/BRAIN_SYNC_STATUS.json`
- `director-os/animatics/15/FONT_STATUS.json`
- `director-os/animatics/15/BUILD_LOG.txt`
- `director-os/animatics/15/FFMPEG_COMMAND.json`

Duration validation:

- master duration: `292.702041s`
- Run 15 duration: `292.657007s`
- difference: `0.045034s`
- status: `ok`
- mode: `full_song`

Review overlay:

- sync-calibrated review
- low-confidence until approved
- caption text includes method, confidence, offset, and unverified status

## Lip-Sync Readiness

Current lip-sync status:

- ready count: 0
- blocked count: 17
- blocker: `blocked_on_low_confidence_sync`

Lip-sync now reads from the calibrated production brain timeline, not blind phrase boundaries.

## Routes

Added/updated:

- `/burmese-language/sync-calibration`
- `/setup/local-asr`
- `/animatic`
- `/lipsync/brain-readiness`

Live route checks:

- `/burmese-language/sync-calibration`: 200
- `/setup/local-asr`: 200
- `/animatic`: 200
- `/director-assets/animatics/15/ANIMATIC_WITH_CAPTIONS_SYNC_CALIBRATED_REVIEW.mp4`: 200 `video/mp4`

## CLI

Added/updated:

- `tools/director-os sync-calibration-status /Users/chan/song-video-project`
- `tools/director-os suggest-caption-offset /Users/chan/song-video-project`
- `tools/director-os apply-caption-offset /Users/chan/song-video-project --seconds <value> --version v6`
- `tools/director-os rebuild-captions /Users/chan/song-video-project --version v6 --sync-calibrated`
- `tools/director-os rebuild-animatic /Users/chan/song-video-project --version 15 --sync-calibrated`
- `tools/director-os local-asr-status`
- `tools/director-os run-local-asr /Users/chan/song-video-project`
- `tools/director-os lipsync-readiness /Users/chan/song-video-project`

## Tests

Passed:

- `python3 -m py_compile $(find director-os-web/app director-os-web/scripts -name '*.py' -print | sort)`
- `cd director-os-web && python3 scripts/smoke_test_local.py`
- live HTTP route/media checks after server restart

Smoke result:

- `smoke ok`
- isolated test database: `director-os-web/data/director_os_test.sqlite`

## Exact Next Action

Open:

- `http://127.0.0.1:8787/burmese-language/sync-calibration`

Review the proposed `+0.800s` offset. If it feels correct, approve it there and rebuild Run 15. If it is still early or late, use the `+/-0.1s`, `+/-0.25s`, or `+/-0.5s` controls and rebuild the review animatic.
