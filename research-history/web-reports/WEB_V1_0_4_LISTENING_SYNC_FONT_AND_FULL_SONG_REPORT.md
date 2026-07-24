# Director OS v1.0.4 Listening Sync, Font, and Full-Song Report

## Problem Confirmed

The reported Run 11 captioned animatic was defective for lyric review.

- Master song: `audio/01.mp3`
- Master song duration: `292.702041` seconds
- Run 11 clean animatic duration: `193.76` seconds
- Run 11 captioned animatic duration: `193.76` seconds
- Run 11 review animatic duration: `193.76` seconds
- Song cut-off confirmed: `yes`
- Cause confirmed: Run 11 ffmpeg command used `-shortest`
- Storyboard timeline duration: `186.57` seconds
- Ending gap after the last current vocal phrase: `159.502041` seconds
- Run 11 status: `superseded_review_defective`

Audit written:

- `director-os-web/ANIMATIC_SYNC_REALITY_AUDIT.md`
- `director-os/animatics/11/SUPERSEDED_STATUS.json`

## Full-Song Repair

A new full-song review animatic was created without overwriting Run 11.

- New animatic version: `12`
- New animatic folder: `director-os/animatics/12/`
- Clean MP4: `director-os/animatics/12/ANIMATIC.mp4`
- Caption review MP4: `director-os/animatics/12/ANIMATIC_WITH_CAPTIONS_REVIEW.mp4`
- Review MP4: `director-os/animatics/12/ANIMATIC_REVIEW.mp4`
- New animatic duration: `292.657007` seconds
- Duration difference from master: `0.045034` seconds
- Duration validation: `ok`
- Mode: `full_song`

The storyboard is shorter than the song, so the repaired build adds a clearly labeled full-song filler/hold section instead of truncating the audio.

## Caption Status

- Caption timing source: `phrase_boundary_local_analysis`
- Caption timing status: `auto_boundary_unverified`
- Verified phrase count: `0`
- Unverified phrase count: `17`
- Wrong-line phrase count: `0`
- Review captions available: `yes`
- Production captions ready: `no`

Caption v3 exports:

- `director-os/captions/final-timing-v3/CAPTIONS_REVIEW.srt`
- `director-os/captions/final-timing-v3/CAPTIONS_REVIEW.vtt`
- `director-os/captions/final-timing-v3/CAPTIONS_REVIEW.ass`
- `director-os/captions/final-timing-v3/CAPTION_FONT_STATUS.json`
- `director-os/captions/final-timing-v3/CAPTION_SYNC_STATUS.json`
- `director-os/captions/final-timing-v3/CAPTION_BLOCKERS.json`

Production captions are blocked until Unicode approval and listening-sync review are completed.

## Burmese Font Status

- Selected font: `Noto Sans Myanmar`
- Font path: `/System/Library/Fonts/NotoSansMyanmar.ttc`
- Readability result: `readable`
- Other detected Burmese-capable fonts:
  - `Myanmar MN`
  - `Myanmar Sangam MN`
- Missing optional font:
  - `Padauk`

The new caption ASS style uses a larger readable size, outline, high contrast, and safer bottom margin.

## Listening Sync

New review route:

- `/burmese-language/listening-sync`

The page provides phrase-by-phrase review with:

- original text
- converted/display text
- pronunciation helper
- start/end/duration
- previous and next gaps
- phrase audio segment
- correct/wrong/timing status controls
- shift/extend/split/merge/instrumental status controls

Current status:

- `auto_boundary_unverified`
- `17` phrases need listening review
- `0` phrases are human-listening verified
- `0` phrases are marked wrong-line

The system no longer claims these captions are human verified, word aligned, syllable aligned, phoneme aligned, or ASR verified.

## Music Analysis

New route:

- `/music-analysis`

Generated:

- `director-os/state/MUSIC_ANALYSIS.json`

Local analysis includes:

- master duration
- RMS energy curve
- 17 vocal phrase regions
- 15 instrumental regions
- intro/outro candidates
- energy peak candidates
- caption regions
- warning that lyric timing is boundary-based, not lyric recognition

No cloud analysis, ASR claim, or lyric-recognition claim was added.

## Voice Sync

Current imported/measured voice files: `0`

Voice sync status:

- `not_tested_no_voice_audio`

Updated route:

- `/captions-voice/sync`

The page now states that voice sync is not tested until real generated or imported audio exists. It can measure WAV/M4A/MP3 imports later with ffprobe and compare them against phrase durations.

## Lip-Sync Readiness

Current lip-sync readiness:

- `blocked_on_phrase_listening_review`

All 17 phrases are blocked by:

- `APPROVED_UNICODE_MISSING`
- `blocked_on_phrase_listening_review`

This is intentional. InfiniteTalk packaging requires approved Unicode, accepted phrase timing, exact audio segments, locked shot timing, and suitable source shots. The system now reports listening review as a real blocker instead of hiding behind only Unicode approval.

## Routes Added Or Updated

- `/animatic`
- `/music-analysis`
- `/burmese-language/listening-sync`
- `/burmese-language/font-check`
- `/captions-voice/sync`

The animatic page now shows the latest safe full-song animatic, duration comparison, font status, sync status, blockers, and links to listening sync and font review.

## CLI Added Or Updated

Validated:

- `tools/director-os animatic-audit /Users/chan/song-video-project`
- `tools/director-os music-analysis /Users/chan/song-video-project`
- `tools/director-os font-check /Users/chan/song-video-project`
- `tools/director-os listening-sync-status /Users/chan/song-video-project`
- `tools/director-os rebuild-animatic /Users/chan/song-video-project --full-song --review-captions`
- `tools/director-os caption-readiness /Users/chan/song-video-project`
- `tools/director-os lipsync-readiness /Users/chan/song-video-project`
- `tools/director-os voice-sync-status /Users/chan/song-video-project`

## Validation

Passed:

- `python3 -m py_compile $(find director-os-web/app director-os-web/scripts -name '*.py' -print | sort)`
- `cd director-os-web && python3 scripts/smoke_test_local.py`

Smoke test result:

- `smoke ok`
- Test database: `director-os-web/data/director_os_test.sqlite`
- No paid API call
- No upload
- No model download
- No source media overwrite

## Preserved Artifacts

- Run 9 preserved
- Run 11 preserved
- Run 11 MP4 files preserved
- Original lyric files preserved
- Existing caption folders preserved
- v1.0.3 timing evidence preserved

## Exact Next User Review Action

Open:

- `/animatic`

Then review:

- `director-os/animatics/12/ANIMATIC_WITH_CAPTIONS_REVIEW.mp4`
- `/burmese-language/listening-sync`

For each phrase, play the phrase audio and answer the practical question:

“Is this the lyric line being sung?”

Only after that review should Director OS promote captions toward production readiness or lip-sync packaging.
