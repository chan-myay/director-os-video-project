# Director OS v1.0.3 Real Zawgyi And Sync Review Report

Date: 2026-07-12

## Summary

v1.0.3 adds a real local conversion/review pipeline and keeps phrase-level timing honest.

Implemented:

- converter adapter stack
- real local rule-based Zawgyi conversion fallback
- exact conversion fixtures
- conversion validation records
- conversion review UI
- phrase-boundary alignment review UI
- estimated syllable markers
- managed voice-audio import and duration measurement
- voice sync classification
- caption `final-timing-v2` review exports
- lip-sync readiness checks
- CLI status commands

Preserved:

- original lyric files
- 29 stored source lines
- 17 timed sung phrases
- local vocal phrase boundary evidence
- Run 9
- Run 11
- existing animatics
- earlier caption folders
- 24/24 lip-sync shot links

## Converter Status

Preferred order implemented:

1. ICU `Zawgyi-my` transliterator through `uconv`
2. PyICU `Zawgyi-my` adapter
3. local Director OS rule-based fallback
4. pass-through only as an explicit failure state

Detected locally:

- ICU `uconv`: unavailable
- PyICU: unavailable
- active converter: `director_os_local_rule_zawgyi_converter`
- active converter version: `1.0.3`

Primary-source references:

- ICU transforms documentation describes ICU general transforms/transliterator identifiers.
- PyICU repository points to the current PyICU project location.
- Google Myanmar Tools is the primary reference for detecting/converting Zawgyi in several languages.

No package was installed.

## Conversion Results

Current project metrics:

- source-line count: 29
- confirmed Unicode count: 5
- confirmed Zawgyi count: 19
- genuinely converted count: 15
- unchanged-but-review-required count: 4
- uncertain/mixed count: 0
- approved count: 5
- blocked phrase count: 17

Important limitation:

The active local fallback is not ICU/Myanmar Tools quality. It performs actual conversion for common Zawgyi patterns in this lyric file, but several converted lines still need human review before production captions are approved.

Pass-through is not labeled as conversion.

## Fixtures

Fixture file:

`director-os-web/app/burmese/fixtures/zawgyi_conversion_fixtures.json`

Covered:

- Unicode no-op
- pre-base vowel ordering
- asat rewrite
- Zawgyi-only codepoint replacement
- kinzi/tone-like cases
- digits/punctuation/English preservation
- ambiguous short text

Fixture pass count: 7/7 in smoke test.

## Review UI

Added:

- `/burmese-language/conversion-review`
- `/burmese-language/alignment`
- `/captions-voice/import`
- `/captions-voice/sync`

Conversion review shows:

- original text
- source category
- detected encoding
- confidence
- converted/normalized Unicode
- warnings
- engine
- approve/edit/reject/mark-original-Unicode actions
- safe bulk approval only for high-confidence validated conversions

## Display Text Rule

Production display priority is now enforced:

1. `user_corrected_unicode`
2. approved converted Unicode
3. validated original Unicode
4. unavailable for production export

Unreviewed Zawgyi does not enter production-approved captions.

## Phrase Timing

The 17 sung phrases are still timed from:

`output/lyric-alignment/vocal-phrase-boundaries.json`

They are labeled:

`phrase_boundary_local_analysis`

They are not labeled word-aligned, syllable-aligned, phoneme-aligned, or ASR-verified.

Timing validation:

- phrase count: 17
- reversed ranges: none
- overlaps: none
- beyond-song-duration warnings: none
- validation status: valid

Approved phrase timings:

- accepted from local boundary analysis: 17
- manually approved: 0

## Syllable Markers

Estimated syllable markers created: 63

Status label:

`estimated_within_phrase`

These are for review/future alignment only, not acoustic syllable timing.

## Voice Import And Sync

Voice import now:

- copies local WAV/MP3/M4A/AAC into managed `director-os/voice-imports/`
- preserves source file
- computes hash
- measures duration
- records sample rate/channels when available
- links to phrase IDs
- classifies sync against target phrase duration

Current project:

- imported voice-file count: 0
- measured voice count: 0
- synchronized voice count: 0

Voice is not called synchronized without real imported/generated audio.

## Caption v2

Created:

`director-os/captions/final-timing-v2/`

Files:

- `CAPTIONS_FINAL_TIMING.srt`
- `CAPTIONS_FINAL_TIMING.vtt`
- `CAPTIONS_FINAL_TIMING.ass`
- `CAPTIONS_FINAL_TIMING.json`
- `CONVERSION_STATUS.json`
- `TIMING_VALIDATION.json`
- `BLOCKED_PHRASES.json`

Caption v2 status:

- production-approved: false
- blocked phrases: 17
- reason: `APPROVED_UNICODE_MISSING`

Earlier caption folders were not intentionally replaced by v2.

## Lip-Sync Readiness

Current readiness:

- ready phrase count: 0
- blocked phrase count: 17
- main blocker: approved Unicode missing

Policy recorded:

InfiniteTalk is driven by the exact approved audio waveform. Phrase boundaries are required to extract the correct audio segment. Phoneme-level Burmese timing is useful for diagnostics but is not the main InfiniteTalk input.

## CLI

Added/verified:

```bash
tools/director-os burmese-converter-status
tools/director-os burmese-conversion-review-status
tools/director-os burmese-convert <file> --preview
tools/director-os rebuild-captions /Users/chan/song-video-project --version v2
tools/director-os lyric-alignment-status /Users/chan/song-video-project
tools/director-os voice-import <audio> --phrase <phrase_id>
tools/director-os voice-sync-status /Users/chan/song-video-project
tools/director-os lipsync-readiness /Users/chan/song-video-project
```

## Tests

Passed:

```bash
python3 -m py_compile $(find director-os-web/app director-os-web/scripts -name '*.py' -print | sort)
```

Passed:

```bash
cd director-os-web
python3 scripts/smoke_test_local.py
```

Smoke test covers:

- exact Zawgyi fixtures
- Unicode no-op
- pass-through not labeled converted
- conversion validation
- phrase timing authority
- caption exports
- lip-sync phrase linking
- fake model isolation
- no cloud API
- no upload
- no model download
- no source lyric overwrite

## Unresolved User Actions

1. Review converted Zawgyi lines at `/burmese-language/conversion-review`.
2. Approve or correct Unicode for the 17 sung lyric phrases.
3. Rebuild caption v2 after approval.
4. Optionally import one real voice audio file at `/captions-voice/import`.
5. Review phrase timing at `/burmese-language/alignment`.

Only after those steps should lip-sync packages be considered production-ready.
