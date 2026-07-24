# Director OS Integrations

Connector layer for future renderers and workflow tools.

v0.3 connectors are stubs only. They do not call APIs, upload media, generate
video, or spend credits.

## Connector Rule

Every real connector must enforce:

- approval gate exists
- exact renderer approved
- exact references approved
- final request approved
- spend limit approved
- privacy warning accepted
- audit log written

## Current Status

See `CONNECTOR_STATUS.yaml`.
