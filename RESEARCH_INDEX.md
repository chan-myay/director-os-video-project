# Research and Evidence Index

This repository contains the real project history required to continue the work.
It is not only a presentation layer.

For route-by-route legacy Advanced coverage, database preservation, and current
truth labels, read `ADVANCED_SYSTEM_COVERAGE.md`.

## Audio Truth

`research-history/audio-truth/` preserves:

- canonical Unicode lyric selection and stale Zawgyi provenance;
- Demucs stem metadata and duration/hash checks;
- Burmese CTC and Whisper model health, transcripts, timestamps, confidence,
  windowing, and ensemble evidence;
- Audio Truth v2, v3, and v4 status files;
- normalized lyric occurrences and repeated-line mapping;
- full-song monotonic path evidence;
- anchor validation and real-user invalidations;
- caption/vocal timing evaluation;
- per-occurrence lyric, pronunciation, meaning, performance direction, timing,
  and validation records;
- lip-sync-ready and blocked occurrence lists;
- package locks and runner code where it existed.

The latest retained state is v4/v2.4.1, not an assertion that alignment is
finished. One early anchor is human-verified. Two replacement anchors passed
technical media validation but still require semantic/timing confirmation. Nine
occurrences are marked ready by the v4 artifact and twelve remain blocked. Two
previous occurrence decisions were explicitly invalidated by real review.

## Lip-sync

`director-os-web/app/lipsync/` contains local, manual, and RunPod InfiniteTalk
provider definitions; provider health; shot eligibility; audio-segment
construction; planning; QC; and job/review integration.

`research-history/lipsync/` preserves generated eligibility maps, plans, lyrics,
pronunciation helpers, job manifests, and segment metadata. WAV segments remain
local because media is intentionally excluded from Git.

The RunPod provider currently reports configuration only and hard-codes
`submission_enabled: false`. Local InfiniteTalk reports non-operational until a
real model benchmark passes. Neither state proves an approved render.

## Face correction

`research-history/face-correction/` and `research-history/tools/` preserve the
model bake-off, DLight training-state metadata, iteration history, progress
tooling, and HiFiFace/UniFace comparison workflow. Model weights, extracted
faces, source photographs, and comparison videos remain private and local.

## Production and failure memory

`research-history/director-os/` preserves foundation maps, asset manifests,
selected-clip inventories, failure/success registers, movement restrictions,
face classifications, safe EDL/timeline review, production state, plans,
evaluations, QC, captions, listening-sync evidence, diagrams, Burmese-language
records, provider research, and license/security decisions.

`research-history/project-state/` preserves lightweight project JSON, concepts,
inputs, scans, storyboards, and status records. Large binaries are represented by
metadata and local paths.

## Web repair history

`research-history/web-reports/` contains route, playback, Burmese encoding, Audio
Truth, autonomous-studio, regression, and Internal Server Error reports. They
are historical evidence, not a claim that every old feature is currently
correct.

## Reading order

1. `PROJECT_HANDOFF.md`
2. `creative-direction/SONG_UNDERSTANDING_AND_NEW_DIRECTION.md`
3. `creative-direction/REARRANGED_EDIT_AND_GENERATION_MATRIX.md`
4. `research-history/audio-truth/v4/AUDIO_TRUTH_V4_STATUS.json`
5. `research-history/audio-truth/v4/anchors/ANCHOR_VALIDATION.json`
6. `research-history/audio-truth/v4/lipsync-segments/LIPSYNC_SEGMENT_STATUS.json`
7. `GPU_SERVER_RUNBOOK.md`
8. `research-history/director-os/director-os-audit/FAILURE_REGISTER.md`
9. `docs/STORAGE_CLEANUP_AUDIT.md`
