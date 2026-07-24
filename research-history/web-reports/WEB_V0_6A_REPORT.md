# Web v0.6A Report

## What Manual Export Does

v0.6A creates a text-only manual renderer export package for
`F01_side_travel_dance`.

It is designed for a human to manually test Seedance or Kling later using:

- exact approved reference file paths and roles
- ready-to-copy request text
- negative lock
- privacy warning
- spend limit note
- QC sheet
- result import instructions

No media is copied into the export folder.

## How User Can Use It

1. Open `/exports/new/F01_side_travel_dance/2`.
2. Create a manual export package.
3. Open the export detail page or export folder.
4. Manually open Seedance or Kling later.
5. Upload only the approved references listed in `REFERENCE_UPLOAD_MANIFEST.md`.
6. Paste the matching request from `FINAL_PLATFORM_REQUEST.md`.
7. Generate one test only.
8. Run `QC_AFTER_GENERATION.md` before creating more attempts.

## Files Created Per Export

Export folder:

`director-os-web/manual-exports/F01_side_travel_dance/<export_id>/`

Files:

- `EXPORT_MANIFEST.yaml`
- `STEP_BY_STEP_UPLOAD_GUIDE.md`
- `FINAL_PLATFORM_REQUEST.md`
- `REFERENCE_UPLOAD_MANIFEST.md`
- `NEGATIVE_LOCK.md`
- `PRIVACY_WARNING.md`
- `SPEND_LIMIT_NOTE.md`
- `QC_AFTER_GENERATION.md`
- `RESULT_IMPORT_INSTRUCTIONS.md`

## What Remains Blocked

- API connectors.
- Cloud upload from Director OS.
- Video generation from Director OS.
- Connector enablement.
- Media copying into export folders.
- Publishing.
- Scraping reference sites.

## Difference From API Connector

Manual export is a human handoff package. It prepares exact instructions and
approved reference paths for a later manual website test.

An API connector would submit files/requests programmatically. v0.6A does not
do that. It only writes local markdown/YAML files and database/audit records.

## Database

Added table:

- `manual_exports`

Fields:

- `export_id`
- `job_id`
- `shot_id`
- `renderer`
- `status`
- `created_at`
- `export_folder`
- `request_file`
- `reference_manifest`
- `qc_file`
- `notes`

## Routes

- `/exports`
- `/exports/new/F01_side_travel_dance/2`
- `/exports/F01_side_travel_dance/{export_id}`

## Exact Test Commands

```bash
cd ~/song-video-project/director-os-web
. .venv/bin/activate
python -m py_compile $(find app scripts -name '*.py' -print | sort)
python scripts/smoke_test_local.py
```

## Exact Run Command

```bash
cd ~/song-video-project/director-os-web
. .venv/bin/activate
./scripts/run_local.sh
```
