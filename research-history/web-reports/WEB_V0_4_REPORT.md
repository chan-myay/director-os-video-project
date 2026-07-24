# Web v0.4 Report

## Database Created

SQLite database:

`director-os-web/data/director_os.sqlite`

Tables:

- `projects`
- `shot_packs`
- `generated_requests`
- `approval_gates`
- `qc_reviews`
- `connector_status`
- `reference_moodboards`
- `audit_logs`

## Routes Added

- `/workflow`
- `/approval-gate/F01_side_travel_dance`
- `/qc/F01_side_travel_dance`
- `/moodboards`
- `/moodboards/new`
- `/connectors/status`
- `/audit-log`

## Forms That Work

- Approval gate record form.
- QC review form.
- URL-only moodboard form.

## Approval Gates

Approval records require:

- renderer selected
- exact references listed
- privacy warning acknowledged
- spend/upload limit entered
- final request reviewed
- explicit approve or reject

Every approval save writes an audit log event.

## QC Reviews

QC records require:

- decision: pass, fail, needs recut, needs face correction, or needs new
  generation
- notes
- identity score
- face risk score
- body risk score
- motion score
- cultural authenticity score
- world-class score

Every QC save writes an audit log event.

## Moodboards

Moodboards store URL records only. They do not copy, download, scrape, or
rehost media.

Fields include title/source, shot-pack relationship, composition, lighting,
camera, color, cultural, rights, and do-not-copy notes.

Every new moodboard URL writes an audit log event.

## Audit Logs

Audit logs are stored in SQLite and shown at `/audit-log`.

Current logged event types:

- `approval_gate_recorded`
- `qc_review_recorded`
- `moodboard_created`

## Still Before Public SaaS

- User accounts and organizations.
- Auth and role-based access.
- PostgreSQL migration.
- Object storage with signed URLs.
- Background workers and job queue.
- Connector API implementation.
- Billing/spend enforcement.
- Admin panel.
- Rights takedown workflow.
- Production deployment hardening.

## Exact Run Commands

```bash
cd ~/song-video-project/director-os-web
. .venv/bin/activate
python scripts/smoke_test_local.py
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
