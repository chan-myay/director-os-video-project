# Public SaaS Architecture

Director OS starts on this Mac as a local development machine, but the structure
must be deployable as a real public SaaS.

## Local Development

- FastAPI backend running locally.
- Jinja frontend for fast product iteration.
- Filesystem readers for the existing `director-os/` engine.
- No media copying by default.
- No renderer execution by default.

## Deployable Backend

- FastAPI service.
- REST API for projects, shot packs, generated requests, references, connectors,
  approvals, QC, jobs, and audit logs.
- Background worker service for future long-running tasks.
- Strict feature flags for cloud connectors and paid API calls.

## Frontend

- Server-rendered FastAPI/Jinja MVP now.
- Later: React/Next.js or similar frontend if collaboration, live review, and
  multi-user editing demand it.

## Database

Local MVP:

- SQLite for product metadata, if/when persistence is needed.
- Current v0.3 reads filesystem evidence only.

SaaS:

- PostgreSQL.
- Tables for users, organizations, projects, assets, references, shot packs,
  generated requests, approvals, connector jobs, QC reviews, audit events, and
  billing gates.

## Storage

Local MVP:

- Existing project filesystem.
- Store paths and metadata, not duplicate media.

SaaS:

- Object storage with project-level isolation.
- Signed URLs.
- Encryption at rest.
- Per-object consent and rights metadata.

## Job Queue

Local MVP:

- No queue yet.

SaaS:

- Redis/RQ, Celery, Dramatiq, or cloud queue.
- Jobs require approval records before execution.
- Workers never infer permission from file presence.

## Worker Layer

Workers handle:

- Request package compilation.
- Thumbnail/contact-sheet generation after approval.
- Connector submission after approval.
- Result ingestion.
- QC prechecks.

Workers do not:

- Upload private media without explicit approval.
- Spend credits without a spend gate.
- Use rejected or child-containing references.

## Renderer Connector Layer

Connectors are adapter classes with a common interface:

- `validate_request`
- `estimate_cost`
- `requires_upload`
- `submit`
- `poll`
- `download_result`

In v0.3 they are stubs only.

## Asset Privacy

- Asset records must carry rights, consent, private/public state, allowed
  connector list, and upload approval state.
- Broad private folders are never uploaded.
- Child-containing sources are blocked.

## Approval And Spend Gates

Every paid/cloud job needs:

- Renderer approval.
- Reference approval.
- Final request approval.
- Spend/credit/time limit.
- Privacy acknowledgement.
- Audit-log entry.

## User Accounts Later

- Email/password or SSO.
- Organization workspaces.
- Role-based access: owner, director, editor, reviewer, admin.

## Project Isolation

- Every asset, job, and generated result belongs to one project.
- Cross-project reference reuse requires explicit duplication or linking with
  rights metadata.

## Admin Panel Later

- User/org management.
- Connector status.
- Cost monitoring.
- Abuse reports.
- Rights takedown workflow.
- Audit log search.

## Audit Logs

Record:

- Who approved a reference.
- Who submitted a job.
- Which connector was used.
- What media was uploaded.
- What spend limit was authorized.
- Which QC criteria passed or failed.
