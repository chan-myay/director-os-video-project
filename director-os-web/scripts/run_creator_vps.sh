#!/usr/bin/env bash
# Private CPU-first Director OS creator: put behind a TLS proxy on a VPS.
set -euo pipefail
cd "$(dirname "$0")/.."
: "${CREATOR_USERNAME:?Set CREATOR_USERNAME}"
: "${CREATOR_PASSWORD:?Set CREATOR_PASSWORD}"
: "${NARA_MINI_ROOT:?Set NARA_MINI_ROOT to the installed Nara Mini v1 directory}"
: "${CREATOR_OUTPUT_ROOT:?Set a private directory outside the web root}"
if [[ "${CREATOR_BIND_HOST:-127.0.0.1}" != "127.0.0.1" && "${CREATOR_BIND_HOST:-}" != "::1" ]]; then
  echo "Refusing public bind. Use a TLS proxy with authentication." >&2; exit 2
fi
exec python -m uvicorn app.creator_server:app --host 127.0.0.1 --port "${CREATOR_PORT:-8788}" --workers 1