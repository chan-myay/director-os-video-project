# Failure Register

This register preserves failures as evidence. Do not delete failed files yet.

## High-Level Failure Pattern

The core failure was asking a probabilistic video generator to solve identity,
body, wardrobe, set design, acting, dancing, camera, singing, and continuity at
the same time. The correction is a staged local Director OS workflow using
existing approved assets, motion references, face correction, and strict review
gates.

## Prompt / Workflow Failures

### Too many objectives in one generation

- Evidence: `output/PRODUCTION-FAILURE-AUDIT.md`
- Result: lead performer identity drift, wardrobe/set/action conflicts, weak continuity.
- Why it failed: references guided generation but did not hard-lock biometric
  identity or body through motion.
- Correction: split identity, motion, body, wardrobe, stage, and edit into
  separate stages.

### Weakened identity wording after policy blocks

- Evidence: P04 and audit notes.
- Result: approximately 60% likeness and wrong performer feel.
- Why it failed: text cannot recover fine facial geometry when identity is not
  strongly conditioned.
- Correction: stop retrying blocked images; do not accept a wrong person.

### Generated singing treated as usable lip-sync

- Evidence: v1 rejection and failure audit.
- Result: fake mouth movement was exposed before real lip-sync.
- Why it failed: prompted singing is not phoneme-accurate Burmese lip-sync.
- Correction: use dedicated lip-sync only after face correction and edit lock.

## Concept / Direction Failures

### Rough cut v1

- File: `production/edit/roughcut-v1/ROUGH-CUT-V1_WITH-MP3.mp4`
- Status: rejected.
- Why it failed:
  - too slow
  - too warm/lounge
  - too microphone-centered
  - fake lip-sync exposed
  - weak face shots exposed
  - did not follow song energy
- Keep/delete/unknown: keep as diagnostic evidence.

### Lounge / karaoke direction

- Evidence: user correction in `RESUME.md`,
  `PROJECT-HANDOFF-COMPLETE-2026-07-07.md`, and
  `production/edit/roughcut-v2/CREATIVE-CORRECTION-BRIEF.md`.
- Why it failed:
  - the song needs rhythm, pressure, and movement
  - microphone-centered staging made the video feel like lounge/karaoke
  - the performer should own the room through dance/performance
- Correction:
  - dance/performance first
  - rhythm first
  - body/stage/movement first
  - microphone as final symbol only

### Wrong dance / wrong movement

- Evidence:
  - Batch E repeated front-facing movement.
  - v2B contact sheet shows repeated front/wide body angles.
  - saved notes say more side-travel/profile/silhouette coverage is missing.
- Why it failed:
  - not enough professional dance coverage
  - too much repeated body language
  - too much reliance on object/face punctuation to fill time
- Correction:
  - do not generate yet
  - when allowed later, use one-shot-at-a-time motion reference workflow
  - inspect normal-speed playback before any next attempt

### Kung fu / Shaolin

- Status: UNKNOWN.
- Inspection result: no matching `kung` or `shaolin` terms were found in the
  required files or inspected markdown notes.
- Evidence gap: if kung fu/Shaolin failures exist only in unlabeled videos or
  outside this repository, they are not documented here.
- Correction:
  - mark UNKNOWN
  - do not infer or invent details
  - preserve all current rejected evidence

## Pilot Failures

### P03 identity drift

- File: `pilot/selected/P03_performer-reveal_take01_SELECTED-BASE.mp4`
- Status: selected as motion/base only.
- Why it failed:
  - wide opening is strong
  - identity drift becomes visible around 00:03
  - later close framing is unacceptable without correction
- Correction:
  - keep P03 as creative/motion base
  - use approved 00:00-00:02.5 wide opening
  - face-correct visible face shots later

### P04 different performer / karaoke emotion / bad blocking

- File: `pilot/rejected/P04_INGREDIENTS_take01_REJECTED-IDENTITY-60PCT.mp4`
- Status: rejected.
- Why it failed:
  - different performer
  - cheerful karaoke emotion
  - bar-floor blocking with unused microphone on empty stage
  - roughly 60% likeness
- Correction:
  - preserve as evidence
  - do not continue this direction

### SimSwap 512 pilot edit

- File: `pilot/selected/edits/P03_PERFORMER-IDENTITY_SIMSWAP512_v1.mp4`
- Status: rejected for final.
- Why it failed:
  - user reported face and lips changed
  - identity was not acceptable
- Correction:
  - preserve as comparison evidence only
  - never use in final edit

## Reference Failures

### Rejected right-profile composite

- File: `references/rejected/REF-A_PERFORMER-IDENTITY-3ANGLE_v1_REJECTED-right-profile.png`
- Status: rejected.
- Why it failed:
  - far-right profile did not resemble lead performer
  - combined sheet contains two approved views but one invalid profile
- Correction:
  - never upload the combined sheet
  - use separate approved front and three-quarter crops only

### Rejected full-body wardrobe v2

- File: `references/rejected/REF-B_PERFORMER-WARDROBE-FULLBODY_v2_REJECTED-face-and-aesthetic.png`
- Status: rejected per asset status; file was not visible in shallow folder
  listing during this audit, so current path should be rechecked before use.
- Why it failed:
  - user reported severe face and aesthetic failure
- Correction:
  - never use as reference
  - keep if present as evidence

## Batch A Failures

Rejected files:

- `production/rejected/batch-a/A04_empty-chair_take01_REJECTED-prop-and-camera-continuity.mp4`
- `production/rejected/batch-a/A09_door-bolt_take01_REJECTED-unlocks-instead-of-locks.mp4`
- `production/rejected/batch-a/A09_door-bolt_take02_REJECTED-entire-housing-slides.mp4`
- `production/rejected/batch-a/A10_empty-microphone_take01_REJECTED-cartoon-props-wrong-stage-no-fade.mp4`

Why they failed:

- prop continuity issues
- wrong lock/unlock behavior
- physically wrong sliding housing
- cartoon props/wrong stage/no fade

Correction:

- keep selected Batch A clips
- preserve rejected files as evidence

## Batch B Failures

Rejected files:

- `production/rejected/batch-b/B01_microphone-half-turn_take01_REJECTED-walks-forward-no-half-turn.mp4`
- `production/rejected/batch-b/B01_microphone-half-turn_take02_REJECTED-doll-like-turn-motion.mp4`
- `production/rejected/batch-b/B01_microphone-half-turn_take03_REJECTED-performer-replacement-magic-disappearance.mp4`
- `production/rejected/batch-b/B06_return-to-stage_take01_REJECTED-back-symbols-hair-and-hem-continuity.mp4`
- `production/rejected/batch-b/B07_rose-placement_take01_REJECTED-microphone-waist-height.mp4`
- `production/rejected/batch-b/B08_curtain-exit_take01_REJECTED-hair-changes-to-bun.mp4`
- `production/rejected/batch-b/B08_curtain-exit_take02_REJECTED-turns-back-and-poses.mp4`

Why they failed:

- wrong action
- doll-like motion
- magic performer replacement
- costume/hair/hem continuity errors
- microphone geometry/height error
- unwanted turn-back pose

Additional caution:

- Most selected Batch B clips have face-identity issues.
- Use selected Batch B only for movement/stage/body/curtain/aisle/rose unless
  local face correction later passes.

## Batch C Failures

Rejected files:

- `production/rejected/batch-c/C02_verse1-frontal-close_take01_REJECTED_wrong-wardrobe-project-direction.mp4`
- `production/rejected/batch-c/C09_chorus-performance-wide_take01_REJECTED_wrong-venue-piano-drums.mp4`
- `production/rejected/batch-c/C09_chorus-performance-wide_OLD-SELECTED_MOVED-TO-REJECTED_wrong-venue-wrong-face.mp4`

Why they failed:

- wrong wardrobe/project direction
- wrong venue
- piano/drums/band elements
- wrong face

Additional caution:

- `C05` has generated mouth/performance movement and should not be treated as
  final lip-sync.
- `C07` first 0-2 seconds are weak identity; use trimmed version only.
- `C09` selected take has stage continuity but face caution; wide/medium only.

## Batch D Failures

Rejected files:

- `production/rejected/batch-d/D02_rhythm-bar-dance_take01_REJECTED_fake-body-proportions_concept-reference.mp4`
- `production/rejected/batch-d/D06_power-chorus-body-silhouette_FULL-TAKE_face-exposed-caution.mp4`

Why they failed:

- D02 was conceptually closer but had fake/exaggerated body shape, especially
  hips/butt/model body.
- Full D06 exposes face near the end and is not safe.

Correction:

- use selected D06 trim only
- keep D02 only as concept/reference evidence, not final footage

## Batch E Failures

Rejected files:

- `production/rejected/batch-e/E01_chorus-bar-dance-wide_take01_REJECTED_repeated-move-face-body-risk.mp4`
- `production/rejected/batch-e/E02_side-travel-dance_take01_REJECTED_fake-body-proportions.mp4`

Why they failed:

- E01 repeated the same front-facing movement and carried face/body risk.
- E02 attempted side travel but produced unusable fake back/hip/butt/body
  proportions.
- User said E02 had "super bad body" and could not be used.

Correction:

- no random credit spending
- do not continue Batch E style
- preserve evidence

## Tooling Failures

From `RESUME.md`:

- macOS AVFoundation could not decode the MOV codec for multi-frame extraction.
- Swift AVAudioFile could not decode the MP3 directly in the available SDK.
- `afconvert` could not create the analysis WAV with tested settings.
- Early Homebrew ffmpeg source build was slow before eventually succeeding.
- Faceswap PNG metadata deserializer failed with NumPy 2.5.1; pinning NumPy
  2.4.0 fixed it.
- Initial DLight iteration-617 output was too blurred for conversion/approval.

Correction:

- use the working ffmpeg path and existing scripts
- do not repeat failed AVFoundation/afconvert paths without a changed method
- keep NumPy pinned where required
- judge face models by moving video, not stills alone

## Privacy / Source-Use Failures and Restrictions

- `IMG_5930.MOV` and `IMG_6737.MOV` contain children and are excluded from
  identity conditioning and generated-scene reference inputs.
- `IMG_6742.MOV` was found to contain a child during extraction context; the
  whole sequence is excluded from training.
- Never upload broad private lead performer source folders to random free tools.

## What Not To Repeat

- Do not redesign the project from scratch.
- Do not return to lounge singer/karaoke/mic-centered staging.
- Do not trust close faces before local face correction.
- Do not use fake generated mouth movement as final lip-sync.
- Do not use rejected profile/composite references.
- Do not spend credits randomly.
- Do not assume face correction can fix fake body, bad movement, bad limbs,
  wrong dress, or wrong stage.
- Do not delete rejected files; they are evidence.
