#!/bin/zsh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STATE="$ROOT/face-correction/work/models/p03-performer-dlight-v1/dlight_state.json"
OUT="$ROOT/face-correction/work/PROGRESS.md"
PY="$ROOT/local-tools/envs/faceswap/bin/python"
TARGET="${TARGET_ITERATIONS:-10363}"

write_status() {
  local current estimated percent remaining updated process state_time elapsed
  current="$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["iterations"])' "$STATE")"
  state_time="$(stat -f '%m' "$STATE")"
  elapsed=$(( $(date '+%s') - state_time ))
  (( elapsed < 0 )) && elapsed=0
  estimated=$(( current + elapsed * 7 / 10 ))
  (( estimated > current + 499 )) && estimated=$(( current + 499 ))
  (( estimated > TARGET )) && estimated="$TARGET"
  percent=$(( estimated * 100 / TARGET ))
  remaining=$(( TARGET - estimated ))
  (( remaining < 0 )) && remaining=0
  updated="$(date '+%Y-%m-%d %H:%M:%S %Z')"

  if ps -axo command 2>/dev/null | grep -F "$ROOT/local-tools/faceswap/faceswap.py train" | grep -v grep >/dev/null; then
    process="running"
  else
    process="stopped"
  fi

  {
    echo "# Face-correction progress"
    echo
    echo "- Updated: $updated"
    echo "- Process: **$process**"
    echo "- Estimated live iteration: **$estimated / $TARGET ($percent%)**"
    echo "- Last confirmed saved iteration: **$current**"
    echo "- Estimated iterations remaining: **$remaining**"
    echo "- Checkpoints save every 500 iterations."
    echo
    echo "Live position is estimated between confirmed 500-iteration checkpoints."
  } > "$OUT.tmp"
  mv "$OUT.tmp" "$OUT"
}

case "${1:-once}" in
  once)
    write_status
    ;;
  watch)
    while true; do
      write_status
      sleep 30
    done
    ;;
  *)
    echo "Usage: $0 [once|watch]"
    exit 2
    ;;
esac
