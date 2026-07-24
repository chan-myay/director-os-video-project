# Director OS v2.2 Burmese Audio Truth Report

## Summary

Director OS v2.2 adds the first self-driving Burmese Audio Truth Engine over the existing Studio workflow.

The engine now:

- audits every lyric-like source it can find in the project,
- selects the newest valid manually edited Unicode lyric file,
- preserves the stale Zawgyi copy as history,
- normalizes phrases without overwriting source text,
- creates occurrence IDs for repeated lyric lines,
- creates one consolidated local audio-model approval,
- prepares local audio-truth folders and normalized full-mix audio,
- blocks Demucs/ASR/CTC until approval instead of guessing,
- builds an `AUDIO_TRUTH_TIMELINE.json`,
- creates lyric verification and meaning/performance maps,
- creates review-only audio-truth caption files,
- creates blocked lip-sync segment manifests for every occurrence,
- creates a new audio-truth review sketch folder,
- updates the Studio UI with an AUDIO UNDERSTANDING stage.

No source lyric, source media, Runs 9-15, Studio Loops 1-2, prior captions, prior animatics, approved/rejected assets, privacy state, consent state, spend gates or QC history were overwritten.

No paid API, cloud upload, substantial model download, Demucs model run, Burmese ASR model run, InfiniteTalk run, or voice cloning was performed.

## Canonical Lyric Source

Selected canonical lyric source:

- `lyrics/အချစ်မဲ့ ဇာတ်လမ်း.txt`

Selection status:

- `selected_newest_valid_manual_unicode`

Encoding:

- `unicode`

Line count:

- `23`

Lyric phrase/occurrence count:

- `21`

Title/credit/section count:

- `2`

Canonical source state file:

- `director-os/state/CANONICAL_LYRIC_SOURCE.json`

Source audit:

- `director-os/state/LYRIC_SOURCE_AUDIT.json`

## Stale Zawgyi Source

Explicit stale source checked:

- `director-os/projects/burmese-music-video/inputs/51b07bfca4c4-Zawgyi.txt`

Status:

- `superseded_stale_retained_for_history`

It is no longer treated as the canonical lyric source for Audio Truth.

## Normalization

Created:

- `director-os/projects/burmese-music-video/audio-truth/NORMALIZED_LYRICS.json`

Stored separately:

- exact source text
- normalized Unicode text
- title/credit/lyric categories
- occurrence IDs
- punctuation
- pronunciation representation
- candidate correction fields
- user-approved correction fields

Repeated lines are not merged. Each repeated line has its own occurrence ID.

## Local Audio-Model Approval

Created:

- `director-os/projects/burmese-music-video/audio-truth/LOCAL_BURMESE_AUDIO_INTELLIGENCE_BUNDLE.json`

Approval status:

- `pending`

The single approval is:

- `LOCAL BURMESE AUDIO INTELLIGENCE BUNDLE`

Detected local tools:

- Demucs executable found: `local-tools/envs/facefusion/bin/demucs`
- FFmpeg found through shared binary discovery
- FFprobe found through shared binary discovery
- MLX Whisper executable exists, but currently reports a Metal-device runtime error in this headless/sandboxed session

Bundle options recorded:

- recommended balanced bundle
- lightweight bundle
- heavier/higher-accuracy bundle

Candidate model sources recorded:

- `YonaKhine/finetuned-w2v2-bert-burmese-asr`
- `Chonlasitk/whisper-burmese`
- `myatsu/whisper-small-burmese-v4`
- Demucs official implementation

No model was downloaded.

## Vocal Separation

Created:

- `director-os/projects/burmese-music-video/audio-truth/stems/full_mix_normalized_16k.wav`
- `director-os/projects/burmese-music-video/audio-truth/stems/separation_metadata.json`

Status:

- `blocked_pending_model_approval`

Reason:

- Demucs execution and any model-weight download require approval of the local audio bundle.

The master song was not modified.

## ASR Ensemble

Created model status folders:

- `director-os/projects/burmese-music-video/audio-truth/asr/YonaKhine-finetuned-w2v2-bert-burmese-asr/`
- `director-os/projects/burmese-music-video/audio-truth/asr/Chonlasitk-whisper-burmese/`
- `director-os/projects/burmese-music-video/audio-truth/asr/myatsu-whisper-small-burmese-v4/`

Status:

- `blocked_pending_bundle_approval`

ASR transcript agreement:

- `not_available_until_models_run`

No ASR output is treated as truth.

## Forced Alignment

Created:

- `director-os/state/AUDIO_TRUTH_TIMELINE.json`

Alignment basis:

- `blocked_until_ctc_asr_bundle_approved`

Occurrence count:

- `21`

High confidence aligned:

- `0`

Medium confidence aligned:

- `0`

Blocked occurrences:

- `21`

Every occurrence records:

- phrase ID
- occurrence ID
- canonical Unicode lyric
- source line
- repeated-line mapping
- previous brain timing only as non-audio-truth evidence
- blockers

No word, syllable or phoneme alignment is claimed.

## Lyric Text Verification

Created:

- `director-os/state/LYRIC_TEXT_VERIFICATION.json`

Status:

- `blocked_pending_audio_model_bundle`

Unresolved count:

- `21`

No meaning-changing correction was applied automatically.

## Meaning, Mood And Performance Map

Created:

- `director-os/state/SONG_MEANING_PERFORMANCE_MAP.json`

Mapped phrase count:

- `21`

Evidence labels used:

- `lyric_semantics`
- `director_inference`
- `uncertain`

No scientific emotion recognition is claimed. The map is a director interpretation grounded in canonical lyric text and the existing approved visual world.

## Captions

Created:

- `director-os/captions/audio-truth-v1/CAPTIONS_AUDIO_TRUTH_REVIEW.srt`
- `director-os/captions/audio-truth-v1/CAPTIONS_AUDIO_TRUTH_REVIEW.vtt`
- `director-os/captions/audio-truth-v1/CAPTIONS_AUDIO_TRUTH_REVIEW.ass`
- `director-os/captions/audio-truth-v1/ALIGNMENT_STATUS.json`
- `director-os/captions/audio-truth-v1/LYRIC_VERIFICATION.json`
- `director-os/captions/audio-truth-v1/CAPTION_BLOCKERS.json`

Production captions:

- not generated

Reason:

- no CTC forced alignment or ASR ensemble evidence has been approved and run.

The review captions do not display ordered lyric lines as if they are synced.

## Lip-Sync

Created:

- `director-os/projects/burmese-music-video/audio-truth/lipsync-segments/`

Ready occurrence count:

- `0`

Blocked occurrence count:

- `21`

Reason:

- exact lyric occurrence timing is not aligned yet.

Every occurrence has local blocked manifests containing:

- lyric text
- pronunciation text
- timing status
- meaning placeholder

No InfiniteTalk package is marked ready.

## Audio-Truth Video Sketch

Created:

- `director-os/projects/burmese-music-video/previews/audio-truth-v1/CREATIVE_SKETCH_AUDIO_TRUTH.mp4`
- `director-os/projects/burmese-music-video/previews/audio-truth-v1/CREATIVE_SKETCH_AUDIO_TRUTH_WITH_CAPTIONS.mp4`
- `director-os/projects/burmese-music-video/previews/audio-truth-v1/CREATIVE_SKETCH_AUDIO_TRUTH_REVIEW.mp4`
- `director-os/projects/burmese-music-video/previews/audio-truth-v1/AUDIO_TRUTH_EVALUATION.json`
- `director-os/projects/burmese-music-video/previews/audio-truth-v1/CAPTION_TIMING_PLOT.png`
- `director-os/projects/burmese-music-video/previews/audio-truth-v1/VOCAL_AND_CAPTION_TIMELINE.png`
- `director-os/projects/burmese-music-video/previews/audio-truth-v1/DURATION_VALIDATION.json`

MP4 metadata:

- duration: `292.657007s`
- resolution: `1920x1080`
- video codec: `h264`
- audio codec: `aac`

Important limitation:

- the audio-truth sketch is review-safe and full-song, but lyric captions are blocked until local ASR/CTC alignment is approved and run.

## Studio UI

Updated:

- `/studio`
- `/studio/projects/burmese-music-video/result`

Added:

- `/studio/projects/burmese-music-video/audio-truth`

The Studio now visibly shows:

- canonical lyric filename
- stale previous source status
- vocal separation status
- model bundle status
- phrase/occurrence count
- caption readiness
- lip-sync readiness
- next action

## Studio Loop

The v2.2 Create Everything path was run on the real project.

Latest Studio Loop:

- loop ID: `4`
- status: `awaiting_approval`
- iterations: `2`
- score: `57.53`

The loop remains stopped at a genuine approval gate because production captions and lip-sync cannot be trusted without the local audio-model bundle.

## Remaining Approval

Single consolidated approval required:

- `LOCAL BURMESE AUDIO INTELLIGENCE BUNDLE`

Approving it would allow Director OS to:

- run Demucs or compatible vocal separation,
- run the approved Burmese ASR ensemble,
- run CTC known-text forced alignment,
- verify lyric text mismatches,
- map repeated chorus occurrences,
- rebuild production-eligible captions where confidence passes,
- create exact master-audio lip-sync segments for aligned occurrences.

## Validation

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

Live route checks:

- `/studio` returned `200`
- `/studio/projects/burmese-music-video/audio-truth` returned `200`
- `/studio/projects/burmese-music-video/result` returned `200`
- `/studio-assets/burmese-music-video/previews/audio-truth-v1/CREATIVE_SKETCH_AUDIO_TRUTH.mp4` returned `200 video/mp4`

## Exact Next Action

Open:

- `http://127.0.0.1:8787/studio/projects/burmese-music-video/audio-truth`

Then approve or decline the single local audio intelligence bundle.

Until that approval is granted:

- production captions remain blocked,
- lip-sync remains blocked,
- Director OS will not pretend the old offset-based captions are true.
