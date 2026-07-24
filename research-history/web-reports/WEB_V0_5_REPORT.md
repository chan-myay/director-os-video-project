# Web v0.5 Report

## Job Tables Created

Added SQLite tables:

- `generation_jobs`
- `job_assets`
- `job_events`
- `job_outputs`

Supported statuses:

- `draft`
- `waiting_approval`
- `approved`
- `dry_run_ready`
- `dry_run_complete`
- `blocked`
- `submitted`
- `running`
- `completed`
- `failed`
- `rejected_by_qc`

v0.5 does not use real `submitted`, `running`, or `completed` connector states.
Only local dry-run statuses are valid in this phase.

## Job Package Files

Each job writes a frozen local package under:

`director-os-web/job-packages/F01_side_travel_dance/<job_id>/`

Files:

- `JOB_MANIFEST.yaml`
- `FINAL_REQUEST.md`
- `APPROVED_REFERENCES.md`
- `PRIVACY_GATE.md`
- `SPEND_GATE.md`
- `NEGATIVE_LOCK.md`
- `QC_TARGET.md`
- `CONNECTOR_DRY_RUN.md`
- `AUDIT_SNAPSHOT.md`

These files store paths, text, gates, and review state only. They do not copy
media.

## Dry-Run Behavior

Dry-run validation:

- validates request metadata
- estimates missing fields
- lists would-upload file paths
- lists privacy risks
- lists cost risk as unknown
- writes `CONNECTOR_DRY_RUN.md`
- writes database events and outputs

It does not upload, call APIs, spend credits, generate video, or run a real
connector.

## Blockers Checked

The asset policy blocks jobs when:

- child-containing source is referenced
- rejected reference sheet is referenced
- broad private lead performer/source folder is referenced
- renderer connector is unknown
- renderer is enabled in v0.5
- spend/upload limit is missing
- privacy acknowledgement is missing
- exact references are missing
- no matching approved approval gate exists for the shot pack and renderer

## Privacy And Spend Protection

Job creation requires a spend/upload limit and privacy acknowledgement. The
package records both in frozen files before any future connector path can be
considered.

All connector records remain disabled/stub. v0.5 dry-run reports what would be
uploaded later but never uploads it.

## Routes Added

- `/jobs`
- `/jobs/new/F01_side_travel_dance`
- `/jobs/F01_side_travel_dance/{job_id}`
- `/jobs/F01_side_travel_dance/{job_id}/dry-run`

## Exact Run Commands

```bash
cd ~/song-video-project/director-os-web
. .venv/bin/activate
./scripts/run_local.sh
```

Open:

```text
http://127.0.0.1:8787
```

## Exact Test Commands

```bash
cd ~/song-video-project/director-os-web
. .venv/bin/activate
python -m py_compile $(find app scripts -name '*.py' -print | sort)
python scripts/smoke_test_local.py
```

## Still Before Real Connector Execution

- Real connector APIs must be verified against official terms.
- Upload approval records need exact file-level consent.
- Cost estimation needs provider-specific pricing.
- Background workers and job queue are still missing.
- Auth, organizations, and project isolation are still local-only placeholders.
- Result ingestion and QC-after-result workflows are not implemented.
- Connectors must remain disabled until the user explicitly approves the
  renderer, references, final request, privacy risk, and spend limit.
