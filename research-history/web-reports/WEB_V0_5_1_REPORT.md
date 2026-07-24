# Web v0.5.1 Report

## What Changed

Added reference completeness and real-generation readiness validation to the
v0.5 job orchestrator.

No video was generated. No API was called. No media was uploaded.

## Required F01 References

`F01_side_travel_dance` now requires:

- `identity_front`: `references/approved/REF-A1_PERFORMER-FACE-FRONT_APPROVED.png`
- `identity_threequarter`: `references/approved/REF-A2_PERFORMER-FACE-THREEQUARTER_APPROVED.png`
- `wardrobe_body`: `references/approved/REF-B_PERFORMER-WARDROBE-FULLBODY_APPROVED.png`
- `bar_stage`: `references/approved/REF-C_BAR-STAGE_APPROVED.png`
- `burmese_art_world`: `references/approved/REF-E_BURMESE-ART-INSERTS_APPROVED.png`

## Package Updates

`APPROVED_REFERENCES.md` now writes references with roles and present/missing
status.

New package file:

- `READINESS_REPORT.md`

The report includes:

- required references
- present references
- missing references
- reference completeness
- real-generation readiness
- blockers

## Dry-Run Updates

`CONNECTOR_DRY_RUN.md` now includes:

- required references
- present references
- missing references
- real-generation readiness: true/false

It still performs no upload, no API call, and no generation.

## Web Route Added

- `/jobs/F01_side_travel_dance/{job_id}/readiness`

## Current Readiness Rule

Reference completeness can be true while real-generation readiness is false.

In v0.5.1 connectors remain disabled, so real generation is blocked until a
future explicit connector approval and implementation phase.

## Validation

Smoke test now:

- creates an F01 job with all five required references
- confirms reference roles are written
- confirms readiness report exists
- confirms no required references are missing
- confirms dry-run report includes reference completeness sections
- confirms no media was copied
- confirms no API/upload/generation

## Exact Commands

```bash
cd ~/song-video-project/director-os-web
. .venv/bin/activate
python -m py_compile $(find app scripts -name '*.py' -print | sort)
python scripts/smoke_test_local.py
./scripts/run_local.sh
```
