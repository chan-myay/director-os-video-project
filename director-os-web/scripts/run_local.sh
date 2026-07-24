#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
export PATH="/Users/chan/song-video-project/local-tools/envs/faceswap/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8787
