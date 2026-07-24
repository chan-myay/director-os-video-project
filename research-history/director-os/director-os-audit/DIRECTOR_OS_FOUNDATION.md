# Director OS Foundation

Purpose: define a local Music Video Director OS foundation for this existing
project without restarting from scratch, without generating new video, and
without calling cloud APIs.

## Mission

Build the final Burmese music video from the existing approved assets, selected
clips, local review evidence, face-correction results, and song analysis.

The OS should protect the project from the failures already documented:

- identity drift
- fake body proportions
- wrong dance/movement
- karaoke/lounge/microphone-centered staging
- fake lip-sync
- prompt drift
- expensive random generation

## Non-Restart Rule

Do not reset the project. Preserve and use:

- `audio/01.mp3`
- approved lead performer face references
- approved red dress/body reference
- approved bar/stage reference
- approved Burmese art reference
- selected P03 safe opening
- selected Batch A/B/C/D material
- face-correction winner decisions
- rough cut v2B as diagnostic evidence

## Core Creative Lock

The current foundation is:

- Burmese heartbreak music video.
- User's lead performer as the lead performer.
- Dark teak bar stage beside Finnish winter.
- Deep red dress.
- Cinematic blues/jazz bar mood, but not lounge/karaoke.
- Dark rhythmic dance/performance energy.
- Black-Swan-style theatrical tension.
- Object story: glasses, rose, empty chair, lock, snow, empty microphone ending.
- Microphone is a symbol only, not the center of performance.

## Director OS Modules

### 1. Asset Registry

Files:

- `director-os-audit/ASSET_MANIFEST.csv`
- `references/ASSET-STATUS.md`
- `production/review/KNOWN-ISSUES-AND-USE-RULES.md`

Jobs:

- track every important asset
- keep status labels: approved, selected, selected-with-caution, rejected,
  restricted, unknown
- prevent rejected assets from re-entering active reference packs
- preserve evidence instead of deleting failures

### 2. Identity Lock

Primary references:

- `references/approved/REF-A1_PERFORMER-FACE-FRONT_APPROVED.png`
- `references/approved/REF-A2_PERFORMER-FACE-THREEQUARTER_APPROVED.png`
- `references/identity-source-selected/IMG_6771.HEIC.png`

Rules:

- never use the rejected three-angle sheet
- never use rejected generated wardrobe/face images
- do not approve close clear faces without normal-speed review
- use HiFiFace 256 primary and UniFace 256 backup for visible-face shots after
  the edit is mostly locked
- never switch face models inside one continuous shot

### 3. Body and Wardrobe Lock

Primary references:

- `references/approved/REF-B_PERFORMER-WARDROBE-FULLBODY_APPROVED.png`
- `references/identity-source-selected/IMG_4079.heic.png`

Rules:

- preserve natural adult proportions
- reject fake/enlarged hips, butt, or model-body reshaping
- face correction cannot fix bad body, bad movement, bad dress, or bad limbs
- selected wide/medium footage must already pass body/stage/movement checks

### 4. Location and Cultural World Lock

Primary references:

- `references/approved/REF-C_BAR-STAGE_APPROVED.png`
- `references/approved/REF-E_BURMESE-ART-INSERTS_APPROVED.png`

Rules:

- dark teak bar, amber practicals, crimson curtain, polished floor, liquor
  shelves, winter window
- Burmese art as material craft, not souvenir decoration
- no piano/drums/band unless explicitly approved later
- no generic lounge singer setup

### 5. Motion Reference Workflow

Existing motion/background assets:

- `pilot/selected/P03_performer-reveal_take01_SELECTED-BASE.mp4`
- `pilot/selected/edits/P03_SAFE-WIDE_00-00_to_00-02.5_v1.mp4`
- `wan-test/input/P03_FIRST-5S_MOTION-BACKGROUND.mp4`
- selected Batch D dance core
- selected Batch B movement-only clips

Workflow:

1. Choose a target song section.
2. Choose existing motion/background or selected footage.
3. Mark face exposure risk.
4. Mark body/movement quality.
5. Decide whether the shot is no-face, face-correctable, or unsafe.
6. Only after review gates, create or request any renderer-specific execution.

No generation happens during this foundation pass.

### 6. Edit OS

Current edit references:

- `production/edit/roughcut-v2/ROUGH-CUT-V2B_DARK-DANCE_LESS-FEET_WITH-MP3.mp4`
- `production/edit/roughcut-v2/ROUGH-CUT-V2B_CONTACT-SHEET_8SEC.jpg`
- `production/edit/roughcut-v2/song-analysis/SONG-ENERGY-MOVEMENT-DIRECTIVES.md`

Rules:

- cut to `audio/01.mp3`
- use object inserts to cover uncertain face/lip moments
- use Batch D as current dance core
- avoid overusing D05 feet/dress
- avoid repeating the same front-facing dance angle
- close emotional shots are punctuation, not the main edit

### 7. Face Correction OS

Current decisions:

- primary: HiFiFace 256
- backup: UniFace 256
- rejected for final: SimSwap 512

Workflow:

1. Lock edit timing first.
2. Identify visible-face shots.
3. Group by continuous shot.
4. For each group, choose HiFiFace primary or UniFace backup.
5. Do not mix models inside one continuous shot.
6. Review normal-speed moving output.
7. Only then prepare final lip-sync candidates.

### 8. Lip-Sync OS

Rules:

- no generated singing is final lip-sync
- only selected medium/close shots get exact sync
- profiles, wide shots, object inserts, silhouettes, and held emotion cover
  uncertain phoneme moments
- final lip-sync happens after face consistency review

### 9. Renderer-Agnostic Prompt Pack System

This audit does not create new prompts. It defines the future pack structure so
generation can happen later without improvisation.

Each future pack should be a folder with:

```text
SHOT_INTENT.md
REFERENCE_PACK.md
MOTION_REFERENCE.md
IDENTITY_RULES.md
BODY_WARDROBE_RULES.md
LOCATION_RULES.md
NEGATIVE_RULES.md
QC_CHECKLIST.md
DECISION_LOG.md
```

Each pack should define fields, not renderer-specific prose first:

- shot id
- song section
- role in edit
- reference images
- motion source
- camera scale
- face exposure level
- body risk level
- stage/location requirements
- reject conditions
- selected/rejected outcome

Renderer adapters can later translate these fields for Flow, Seedance, Runway,
Pika, local Wan, or another tool. The creative truth stays renderer-agnostic.

### 10. Review Gates

Every shot or asset must pass these gates:

1. Correct project world.
2. Correct lead performer identity or safe non-face usage.
3. Correct natural body proportions.
4. Correct red dress.
5. Correct bar/stage or approved object world.
6. Correct movement energy.
7. No fake lip-sync exposure.
8. No microphone-centered performance unless ending symbol.
9. Normal-speed playback review.
10. Written accept/reject note.

## Local Directory Proposal

Future Director OS work can stay local under:

```text
director-os-audit/
director-os/
director-os/assets/
director-os/shot-packs/
director-os/reviews/
director-os/edit-decisions/
director-os/face-correction/
```

Do not create this expanded structure until needed. For now, this audit folder
is enough.

## Immediate Operating Rule

No new generation yet. The next work should be audit, organization, review,
shot inventory, and practical planning only.
