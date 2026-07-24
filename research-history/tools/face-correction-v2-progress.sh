#!/bin/zsh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STATE="$ROOT/face-correction/v2/models/p03-performer-dlight-384-v2/dlight_state.json"
OUT="$ROOT/face-correction/v2/PROGRESS.md"
PY="$ROOT/local-tools/envs/faceswap/bin/python"
TRAIN_CMD="$ROOT/local-tools/faceswap/faceswap.py train"
TARGET=5000

current="$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["iterations"])' "$STATE")"
state_time="$(stat -f '%m' "$STATE")"
elapsed=$(( $(date '+%s') - state_time ))
(( elapsed < 0 )) && elapsed=0

# Measured v2 throughput is approximately 0.8 iterations/second.
estimated=$(( current + elapsed * 4 / 5 ))
(( estimated > current + 499 )) && estimated=$(( current + 499 ))
(( estimated > TARGET )) && estimated=$TARGET
remaining=$(( TARGET - estimated ))
percent=$(( estimated * 100 / TARGET ))
minutes=$(( (remaining * 5 / 4 + 59) / 60 ))

if ps -axo command 2>/dev/null | grep -F "$TRAIN_CMD" | grep -v grep >/dev/null; then
  process="running"
else
  process="stopped"
fi

{
  echo "# Face-correction v2 progress"
  echo
  echo "- Updated: $(date '+%Y-%m-%d %H:%M:%S %Z')"
  echo "- Process: **$process**"
  echo "- Estimated live iteration: **$estimated / $TARGET ($percent%)**"
  echo "- Last confirmed saved iteration: **$current**"
  echo "- Estimated time remaining: **about $minutes minutes**"
  echo "- Model: **DLight 384 px, batch 2**"
  echo "- Source faces: **492**"
  echo
  echo "Live position is estimated between confirmed 500-iteration checkpoints."
} > "$OUT.tmp"
mv "$OUT.tmp" "$OUT"

