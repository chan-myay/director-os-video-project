# MVP Definition

## MVP Goal

Build a serious local-first Director OS web app that reads existing engine
evidence, displays shot packs, generated request packages, connectors, reference
library strategy, approval gates, and QC.

## In Scope

- FastAPI local app.
- Dashboard.
- Product docs viewer.
- Shot pack list and detail.
- Generated request viewer.
- Reference library status.
- Connector status.
- Approval gate view.
- QC view.
- No media copying.
- No renderer execution.

## Out Of Scope

- Video generation.
- Paid APIs.
- Uploads.
- GitHub publishing.
- User accounts.
- Database persistence.
- Billing.
- Worker queue.

## Success Criteria

- User can inspect the engine from a browser.
- F01 compiled request is visible.
- Approval gates are visible before renderer request files.
- Connectors show disabled/stub status.
- Product architecture is documented for SaaS growth.

## Next MVP After v0.3

- Add persistent project metadata.
- Add manual approval records.
- Add connector cost estimate stubs.
- Add reference moodboard CRUD without media scraping.
