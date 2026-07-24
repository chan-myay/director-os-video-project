# Director OS Web v0.6A.1 Report

## Purpose

v0.6A.1 corrects the manual renderer export workflow so a package cannot be
treated as production-ready just because a text bundle exists.

No API calls were added. No uploads were performed. No video was generated. No
source media was modified.

## What Changed

- Replaced loose `manual_ready` behavior with explicit export readiness states:
  `draft`, `blocked`, `review_ready`, `production_ready`, `exported`,
  `superseded`.
- Added structured spend/upload approval fields to manual exports:
  approved renderer, max generation count, max duration, max spend, exact cloud
  upload approval, privacy acknowledgement, and approval timestamp.
- Added F01 motion-reference enforcement.
- Added motion-reference database/UI pages:
  `/motion-references`, `/motion-references/new`, and
  `/shot-packs/F01_side_travel_dance/motion-reference`.
- Added renderer-specific export packages for Seedance and Kling Motion Control.
- Added production-readiness reports and blocked upload guides.
- Removed Black-Swan-style movement instruction from F01 export requests. F01
  movement must come from the approved motion-reference video.
- Corrected Export #3 as preserved evidence, not a usable production package.

## Production-Readiness Blocking

Production readiness is blocked when spend/upload approval contains or implies:

- smoke test
- dry-run only
- no upload
- no spend
- UNKNOWN
- blank spend value

F01 is also blocked until it has one approved motion-reference video with:

- exact usable start/end timecode
- left-to-right or right-to-left travel direction
- full-body or medium-wide framing
- rights status and source owner/license
- approved transfer of body movement, timing, travel path, and shoulder/torso
  rhythm
- explicit non-transfer of source identity, clothing, location, and body shape

## Renderer-Specific Enforcement

Seedance exports now include:

- `INPUT_MAPPING_SEEDANCE.md`
- `FINAL_SEEDANCE_REQUEST.md`
- `SEEDANCE_SETTINGS.md`

Seedance requires identity front, identity three-quarter, body/wardrobe,
bar/stage, Burmese art world, and approved motion-reference video.

Kling Motion Control exports now include:

- `INPUT_MAPPING_KLING_MOTION_CONTROL.md`
- `FINAL_KLING_MOTION_CONTROL_REQUEST.md`
- `KLING_SETTINGS.md`

Kling is blocked until an approved `character_start_frame` exists with full-body
performer, correct deep-red dress, correct bar/stage, enough lateral floor
space, body scale matching the motion reference, no children, and approved
identity state.

## Export Files

Every export now writes production-readiness evidence files:

- `PRODUCTION_READINESS_REPORT.md`
- `MOTION_REFERENCE_MANIFEST.md`
- `RENDERER_INPUT_MAPPING.md`
- `PLATFORM_SETTINGS.md`
- `FINAL_RENDERER_REQUEST.md`
- `APPROVED_UPLOAD_LIST.md`
- `SPEND_APPROVAL.md`
- `PRIVACY_APPROVAL.md`
- `QC_AFTER_GENERATION.md`

Blocked exports keep evidence files but hide actionable upload instructions.

## Export #3 Correction

Existing Export #3 was marked:

- status: `superseded`
- readiness status: `blocked`

Recorded reasons:

- `INVALID_SMOKE_TEST_SPEND_GATE`
- `MISSING_MOTION_REFERENCE`
- `RENDERER_PACKAGE_NOT_SPECIALIZED`
- `KLING_CHARACTER_START_FRAME_NOT_APPROVED`

The export was not deleted.

## Connector Matrix Correction

The connector matrix now treats Seedance 2.0 as having an official API path
through BytePlus ModelArk. Implementation status remains `not connected`.
Credential, spend, region, privacy, and terms review are still required.

The Seedance connector remains disabled.

## Validation

Commands run:

```bash
python3 -m py_compile $(find director-os-web/app director-os-web/scripts -name '*.py' -print | sort)
cd director-os-web && python3 scripts/smoke_test_local.py
```

Smoke test confirmed:

- smoke-test spend gate cannot become `production_ready`
- F01 without motion video is blocked
- Seedance without motion video is blocked
- Kling without character start frame is blocked
- Seedance and Kling mappings are different
- manual export folders contain no copied media
- no API call, upload, or generation occurred
- test data used `director_os_test.sqlite`

## Remaining Blockers

- F01 still needs an approved motion-reference video record.
- Kling still needs an approved character/start-frame image.
- Real cloud generation still requires explicit renderer, privacy, upload, and
  spend approval.
- API connectors remain disabled.
