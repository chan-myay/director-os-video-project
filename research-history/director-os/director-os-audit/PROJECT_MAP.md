# Project Map

Audit date: 2026-07-10

Scope: read-only inspection plus new audit files in `director-os-audit/`.
No existing project media was deleted, moved, overwritten, generated, uploaded,
or sent to any cloud API.

## Current Working Truth

- Master song: `audio/01.mp3`
- Best current diagnostic cut:
  `production/edit/roughcut-v2/ROUGH-CUT-V2B_DARK-DANCE_LESS-FEET_WITH-MP3.mp4`
- Rough cut v1 is rejected:
  `production/edit/roughcut-v1/ROUGH-CUT-V1_WITH-MP3.mp4`
- Current usable dance core: selected Batch D.
- Batch E is rejected.
- No new video generation should happen yet.
- Existing Batch F prep files exist, but this audit does not create new video
  prompts or run generation.

## Top-Level Folder Map

```text
.
audio/
director-os-audit/
face-correction/
ideas/
local-tools/
lyrics/
output/
pilot/
production/
references/
tools/
wan-test/
```

## Folder Purposes

### `audio/`

Purpose: master audio and analysis audio.

Important assets:

- `audio/01.mp3` - active final song master.
- `audio/01-analysis.wav` - derived analysis WAV; not the edit master.

### `lyrics/`

Purpose: lyric source material.

Important assets:

- `lyrics/အခ်စ္မဲ့ ဇာတ္လမ္း - Zawgyi.txt` - preserved Zawgyi lyrics.

### `references/`

Purpose: source references, approved references, rejected references, contact
sheets, and working conversions.

Structure:

```text
references/
references/Dress/
references/My lead performer/
references/My lead performer/interviews/
references/approved/
references/drafts/
references/identity-source-selected/
references/rejected/
references/working-lead performer-jpeg/
references/working-lead performer-video-frames/
references/working-lead performer-video-frames/IMG_4085/
references/working-lead performer-video-frames/IMG_5930/
references/working-lead performer-video-frames/IMG_6347/
references/working-lead performer-video-frames/IMG_6417/
references/working-lead performer-video-frames/IMG_6707/
references/working-lead performer-video-frames/IMG_6737/
references/working-lead performer-video-frames/IMG_6742/
```

Important assets:

- `references/approved/REF-A1_PERFORMER-FACE-FRONT_APPROVED.png`
- `references/approved/REF-A2_PERFORMER-FACE-THREEQUARTER_APPROVED.png`
- `references/approved/REF-B_PERFORMER-WARDROBE-FULLBODY_APPROVED.png`
- `references/approved/REF-C_BAR-STAGE_APPROVED.png`
- `references/approved/REF-E_BURMESE-ART-INSERTS_APPROVED.png`
- `references/identity-source-selected/IMG_4079.heic.png`
- `references/identity-source-selected/IMG_6771.HEIC.png`
- `references/working-lead performer-contact-sheet.png`

Known reference cautions:

- `references/rejected/REF-A_PERFORMER-IDENTITY-3ANGLE_v1_REJECTED-right-profile.png`
  must not be uploaded or used as a reference.
- `references/Dress/` contains stock/watermarked idea references. Use only for
  broad pose, light, and dress-energy thinking; do not copy exact images.
- `references/My lead performer/IMG_5930.MOV` and `references/My lead performer/IMG_6737.MOV`
  contain children per saved notes and are excluded from identity conditioning.
- `references/My lead performer/IMG_6742.MOV` was found to contain a child in face
  extraction context; the complete sequence is excluded from training.

### `pilot/`

Purpose: first pilot generations, keyframes, selected safe segment, rejected
pilot, and face-corrected pilot versions.

Structure:

```text
pilot/
pilot/keyframes/
pilot/raw/
pilot/rejected/
pilot/review/
pilot/review/P03_detailed/
pilot/review/P03_take01_frames/
pilot/review/P04_frames/
pilot/selected/
pilot/selected/edits/
```

Important assets:

- `pilot/selected/P03_performer-reveal_take01_SELECTED-BASE.mp4` - locked
  creative/motion base.
- `pilot/selected/edits/P03_SAFE-WIDE_00-00_to_00-02.5_v1.mp4` - explicitly
  approved safe wide opening.
- `pilot/selected/P03_FINAL-SELECTED_FULL-HIFIFACE256_v1.mp4` - primary
  full-shot selected pilot with approved HiFiFace 256 correction.
- `pilot/rejected/P04_INGREDIENTS_take01_REJECTED-IDENTITY-60PCT.mp4` - rejected
  for identity and performance/staging problems.
- `pilot/selected/edits/P03_PERFORMER-IDENTITY_SIMSWAP512_v1.mp4` - rejected for
  final use; kept only as comparison evidence.

### `production/`

Purpose: raw generated batches, selected clips, rejected clips, review sheets,
rough cuts, and current edit diagnostics.

Structure:

```text
production/
production/continuity/
production/edit/
production/edit/roughcut-v1/
production/edit/roughcut-v1/segments/
production/edit/roughcut-v2/
production/edit/roughcut-v2/audio-analysis/
production/edit/roughcut-v2/segments/
production/edit/roughcut-v2/segments-v2b/
production/edit/roughcut-v2/song-analysis/
production/raw/
production/raw/batch-a/
production/raw/batch-b/
production/raw/batch-c/
production/raw/batch-d/
production/raw/batch-e/
production/raw/batch-f/
production/rejected/
production/rejected/batch-a/
production/rejected/batch-b/
production/rejected/batch-c/
production/rejected/batch-d/
production/rejected/batch-e/
production/rejected/batch-f/
production/review/
production/review/batch-a/
production/review/batch-b/
production/review/batch-c/
production/review/batch-d/
production/review/batch-e/
production/review/batch-f/
production/selected/
production/selected/batch-a/
production/selected/batch-b/
production/selected/batch-c/
production/selected/batch-d/
production/selected/batch-e/
production/selected/batch-f/
```

Important assets:

- Batch A selected clips - atmosphere/object/story cutaways.
- Batch B selected clips - movement/stage only; faces not trusted.
- Batch C selected clips - emotional punctuation; close faces still need
  correction review.
- Batch D selected clips - current best dance core.
- Batch E rejected clips - repeated movement and bad body proportions.
- `production/review/KNOWN-ISSUES-AND-USE-RULES.md` - active use rules.
- `production/edit/roughcut-v2/CREATIVE-CORRECTION-BRIEF.md` - current creative
  correction.
- `production/edit/roughcut-v2/ROUGH-CUT-V2B_DARK-DANCE_LESS-FEET_WITH-MP3.mp4`
  - current best diagnostic rough cut.
- `production/edit/roughcut-v2/ROUGH-CUT-V2B_CONTACT-SHEET_8SEC.jpg` - quick
  sheet showing current repetition and missing coverage.
- `production/raw/batch-f/BATCH-F-PROMPTS-AND-QC.md` - existing prepared Batch F
  prompt/QC file. This audit does not add to it.
- `production/review/batch-f/BATCH-F-STATUS.md` - existing Batch F status.

### `face-correction/`

Purpose: local face replacement/correction experiments, extracted source and
target frames, model bake-off outputs, progress logs, and DLight training.

Structure:

```text
face-correction/
face-correction/facefusion-tests/
face-correction/model-bakeoff/
face-correction/model-bakeoff/logs/
face-correction/model-bakeoff/source/
face-correction/model-bakeoff/videos/
face-correction/source-lead performer/
face-correction/source-lead performer/IMG_4085/
face-correction/source-lead performer/IMG_6707/
face-correction/source-lead performer/IMG_6742/
face-correction/source-lead performer/stills/
face-correction/target-p03/
face-correction/v2/
face-correction/v2/logs/
face-correction/v2/models/
face-correction/v2/output/
face-correction/v2/source-IMG_6706-faces/
face-correction/v2/source-IMG_6706-frames/
face-correction/v2/source-combined/
face-correction/work/
face-correction/work/models/
face-correction/work/output/
face-correction/work/review-IMG_6706/
face-correction/work/review-interviews/
face-correction/work/source-lead performer/
face-correction/work/target-p03/
```

Important assets:

- `face-correction/model-bakeoff/videos/05_hififace_unofficial_256.mp4` -
  primary approved face-correction candidate.
- `face-correction/model-bakeoff/videos/13_uniface_256.mp4` - approved backup.
- `face-correction/model-bakeoff/videos/10_inswapper_128_fp16.mp4` - formerly
  shortlisted; not final primary.
- `face-correction/model-bakeoff/videos/12_simswap_unofficial_512.mp4` and
  `pilot/selected/edits/P03_PERFORMER-IDENTITY_SIMSWAP512_v1.mp4` - comparison only,
  not final.
- `face-correction/work/models/p03-performer-dlight-v1/` - first DLight local model
  family; early checkpoint was not a quality pass.
- `face-correction/v2/models/p03-performer-dlight-384-v2/` - later v2 DLight model
  family.
- `face-correction/target-p03/` - 192 target frames.

### `wan-test/`

Purpose: staged input for a future Wan2.2-Animate replacement test. No current
audit action runs this.

Important assets:

- `wan-test/input/P03_FIRST-5S_MOTION-BACKGROUND.mp4`
- `wan-test/input/PERFORMER-FACE-FRONT-REFERENCE.png`
- `wan-test/input/PERFORMER-IDENTITY-BODY-REFERENCE.png`

### `output/`

Purpose: research, planning, continuity, audio/lyric analysis, and production
documents.

Important assets:

- `output/PRODUCTION-FAILURE-AUDIT.md`
- `output/COMMERCIAL-CONTINUITY-PROTOCOL.md`
- `output/MASTER-MUSIC-VIDEO-SCRIPT.md`
- `output/AUDIO-RHYTHM-ANALYSIS.md`
- `output/LYRIC-PHRASE-TIMING-DRAFT.md`
- `output/LIPSYNC-PERFORMANCE-PLAN.md`
- `output/IDENTITY-PIPELINE-RESEARCH.md`
- `output/lyric-alignment/`
- `output/vocal-separation/`

### `tools/`

Purpose: local scripts for audio analysis, rough-cut rendering, face-correction
progress, contact sheets, and model comparisons.

Important assets:

- `tools/render-roughcut-v1.sh`
- `tools/render-roughcut-v2.sh`
- `tools/render-roughcut-v2b.sh`
- `tools/run-face-model-bakeoff.sh`
- `tools/face-correction-local.sh`
- `tools/face-correction-progress.sh`
- `tools/face-correction-v2-progress.sh`
- `tools/analyze-song-energy.py`
- `tools/detect-vocal-phrases.py`
- `tools/make_contact_sheet.swift`

### `local-tools/`

Purpose: local dependencies and cloned tools. This is large dependency/runtime
state, not creative source.

Structure:

```text
local-tools/
local-tools/conda-home/
local-tools/conda-pkgs/
local-tools/envs/
local-tools/facefusion/
local-tools/faceswap/
local-tools/miniforge3/
local-tools/pip-cache/
```

Important assets:

- `local-tools/faceswap/` - cloned Faceswap source.
- `local-tools/facefusion/` - cloned FaceFusion source.
- `local-tools/envs/faceswap/` - project-local environment used by render and
  face-correction scripts.

Do not clean this folder without a separate dependency audit.

### `ideas/`

Purpose: older concept notes.

Important assets:

- `ideas/original-idea.txt`
- `ideas/creative-direction-v1.md`

These are useful evidence but superseded by the current dark rhythmic
bar-stage direction.

### `director-os-audit/`

Purpose: this audit package.

Expected files:

```text
director-os-audit/PROJECT_MAP.md
director-os-audit/ASSET_MANIFEST.csv
director-os-audit/SUCCESS_REGISTER.md
director-os-audit/FAILURE_REGISTER.md
director-os-audit/DIRECTOR_OS_FOUNDATION.md
director-os-audit/NEXT_10_STEPS.md
```

## File Count Snapshot

Approximate file counts by top-level folder from inspection:

| Folder | Files |
|---|---:|
| `audio/` | 2 |
| `face-correction/` | 2588 |
| `ideas/` | 2 |
| `local-tools/` | 142120 |
| `lyrics/` | 2 |
| `output/` | 21 |
| `pilot/` | 36 |
| `production/` | 306 |
| `references/` | 313 |
| `tools/` | 17 |
| `wan-test/` | 4 |

## Important Asset Categories

- Master audio: `audio/01.mp3`
- Identity references: `references/approved/REF-A1...`,
  `references/approved/REF-A2...`
- Body/wardrobe reference: `references/approved/REF-B...`
- Bar/stage reference: `references/approved/REF-C...`
- Burmese art reference: `references/approved/REF-E...`
- Real lead performer source library: `references/My lead performer/`,
  `references/identity-source-selected/`, extracted frame folders.
- Motion base: `pilot/selected/P03_performer-reveal_take01_SELECTED-BASE.mp4`
- Safe pilot opening: `pilot/selected/edits/P03_SAFE-WIDE_00-00_to_00-02.5_v1.mp4`
- Current face-corrected pilot: `pilot/selected/P03_FINAL-SELECTED_FULL-HIFIFACE256_v1.mp4`
- Current selected production clips: `production/selected/batch-a/`,
  `batch-b/`, `batch-c/`, `batch-d/`
- Current rejected evidence: `production/rejected/`, `pilot/rejected/`,
  `references/rejected/`
- Face-correction winners: HiFiFace 256 primary, UniFace 256 backup.
- Current diagnostic cut: v2B in `production/edit/roughcut-v2/`.

## Preservation Rule

Do not delete anything yet. Files with obvious rejection labels are still useful
as evidence for what failed, why it failed, and what not to repeat.
