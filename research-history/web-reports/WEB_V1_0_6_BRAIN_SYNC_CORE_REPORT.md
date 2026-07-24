# Director OS v1.0.6 Brain Sync Core Report

## Purpose

This patch responds to the Run 13 review problem: captions were still ahead of the singing and the system was relying too much on estimated phrase boundaries. v1.0.6 creates one shared production brain timeline for music, lyrics, emotion, captions, shot mapping, and lip-sync readiness.

No storyboard model, InfiniteTalk model, voice model, paid API, cloud upload, or source-media overwrite was performed.

## Run 13 Problem

- User review reported Run 13 captions were ahead of the singing.
- Director OS now records that as production feedback and uses local waveform/RMS onset evidence only as support.
- The system still does not claim word, syllable, phoneme, or ASR alignment.

## Brain Timeline

Created:

- `director-os/state/PRODUCTION_BRAIN_TIMELINE.json`
- `director-os/state/SYNC_OFFSET_ANALYSIS.json`
- `director-os/state/LYRIC_MEANING_EMOTION_MAP.json`

The brain timeline now stores:

- master song duration
- song sections
- vocal phrase regions
- lyric phrase IDs
- approved/review Unicode text
- pronunciation helper
- rough meaning and emotion labels
- phrase start/end
- caption display timing
- shot/storyboard relationship
- lip-sync segment timing
- voice segment status
- blockers
- evidence and confidence

## Offset Detection

- Captions-ahead condition: detected from user report plus local RMS/onset evidence.
- Global caption delay applied in review timing: `+0.405s`
- Drift estimate: `0.42s/minute`
- Offset confidence: `0.62`
- Safe auto-apply for review: `true`
- Production approval still required: yes

The correction is applied to Run 14 review captions, but every phrase remains review-only until listening approval.

## Sync Method Counts

- `boundary_plus_global_offset`: 17 phrases
- high-confidence phrases: 0
- low-confidence phrases: 17
- blocked phrases: 17

Block reason:

- `LOW_CONFIDENCE_ALIGNMENT`

## Captions v5

Created:

- `director-os/captions/final-timing-v5/CAPTIONS_REVIEW_BRAIN_SYNC.srt`
- `director-os/captions/final-timing-v5/CAPTIONS_REVIEW_BRAIN_SYNC.vtt`
- `director-os/captions/final-timing-v5/CAPTIONS_REVIEW_BRAIN_SYNC.ass`
- `director-os/captions/final-timing-v5/BRAIN_SYNC_STATUS.json`
- `director-os/captions/final-timing-v5/OFFSET_ANALYSIS.json`
- `director-os/captions/final-timing-v5/CAPTION_BLOCKERS.json`

Production captions remain blocked because:

- all 17 phrase timings are low-confidence brain sync
- Unicode review is still not fully production-approved

## Animatic v14

Created:

- `director-os/animatics/14/ANIMATIC.mp4`
- `director-os/animatics/14/ANIMATIC_WITH_CAPTIONS_BRAIN_SYNC_REVIEW.mp4`
- `director-os/animatics/14/ANIMATIC_REVIEW.mp4`
- `director-os/animatics/14/BRAIN_SYNC_STATUS.json`
- `director-os/animatics/14/OFFSET_ANALYSIS.json`
- `director-os/animatics/14/DURATION_VALIDATION.json`
- `director-os/animatics/14/FONT_STATUS.json`
- `director-os/animatics/14/BUILD_LOG.txt`
- `director-os/animatics/14/FFMPEG_COMMAND.json`
- `director-os/animatics/14/MEDIA_METADATA.json`

Duration validation:

- master duration: `292.702041s`
- Run 14 animatic duration: `292.657007s`
- difference: `0.045034s`
- status: `ok`
- mode: `full_song`

Run 14 is full-song and does not overwrite Run 9, Run 11, Run 12, or Run 13.

## Music And Emotion

The brain timeline links each phrase to:

- local music-analysis evidence
- rough meaning category
- emotional meaning label
- music energy summary
- performance direction
- shot purpose
- lip-sync importance

This is director-inferred and evidence-labeled. It is not claimed as automatic emotion recognition.

## ASR Status

Added local ASR adapter interfaces:

- `whisper_cli`
- `mlx_whisper`
- `whisper_cpp`
- `mock_asr`

No ASR model was downloaded or installed. `/setup/local-asr` shows the consolidated setup decision. Burmese ASR support is not marked verified.

## UI And CLI

Added/updated:

- `/music-analysis/brain`
- `/setup/local-asr`
- `/lipsync/brain-readiness`
- `/burmese-language/listening-sync`
- `/animatic`
- Command Center brain-sync status

CLI added/updated:

- `tools/director-os brain-sync /Users/chan/song-video-project`
- `tools/director-os brain-sync-status /Users/chan/song-video-project`
- `tools/director-os apply-caption-offset /Users/chan/song-video-project --seconds <value>`
- `tools/director-os rebuild-captions /Users/chan/song-video-project --version v5 --brain-sync`
- `tools/director-os rebuild-animatic /Users/chan/song-video-project --version 14 --brain-sync`
- `tools/director-os music-brain /Users/chan/song-video-project`
- `tools/director-os lipsync-readiness /Users/chan/song-video-project`

## Lip-Sync Readiness

Lip-sync readiness now reads from `PRODUCTION_BRAIN_TIMELINE.json`.

Current status:

- ready count: 0
- blocked count: 17
- reason: `blocked_on_low_confidence_alignment`

Voice sync remains:

- `not_tested_no_voice_audio`

## Tests

Passed:

- `python3 -m py_compile $(find director-os-web/app director-os-web/scripts -name '*.py' -print | sort)`
- `cd director-os-web && python3 scripts/smoke_test_local.py`
- route import/render checks for `/animatic`, `/music-analysis/brain`, `/burmese-language/listening-sync`, `/setup/local-asr`, `/lipsync/brain-readiness`
- Run 14 media serving checks
- CLI brain-sync checks

Smoke result:

- `smoke ok`
- isolated test database: `director-os-web/data/director_os_test.sqlite`

## Next User Action

Open:

- `http://127.0.0.1:8787/director-assets/animatics/14/ANIMATIC_WITH_CAPTIONS_BRAIN_SYNC_REVIEW.mp4`

Then review:

- `http://127.0.0.1:8787/burmese-language/listening-sync`

If captions are still early or late, use the global shift controls there. Director OS will preserve that feedback in `director-os/state/SYNC_FEEDBACK.json` and rebuild from the brain timeline.
