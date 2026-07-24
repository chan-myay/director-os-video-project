#!/bin/zsh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/local-tools/envs/faceswap/bin/python"
FS="$ROOT/local-tools/faceswap/faceswap.py"
MODEL="$ROOT/face-correction/work/models/p03-performer-dlight-v1"
STATE="$MODEL/dlight_state.json"
TARGET_FACES="$ROOT/face-correction/work/target-p03/faces"
SOURCE_FACES="$ROOT/face-correction/work/source-lead performer/faces-curated"
TARGET_FRAMES="$ROOT/face-correction/target-p03"
ALIGNMENTS="$ROOT/face-correction/work/target-p03/alignments.fsa"
OUTPUT="$ROOT/face-correction/work/output/p03-performer-dlight-v1-frames"
LOG="$MODEL/p03-performer-dlight-v1-train.log"

export HOME="$ROOT/local-tools/conda-home"
export KERAS_HOME="$HOME/.keras"

current_iteration() {
  "$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["iterations"])' "$STATE"
}

status() {
  local current
  current="$(current_iteration)"
  echo "Saved iteration: $current"
  if pgrep -f "$FS train" >/dev/null 2>&1; then
    echo "Training process: running"
  else
    echo "Training process: stopped"
  fi
}

train_to() {
  local target="$1"
  local current remaining
  current="$(current_iteration)"
  remaining=$(( target - current ))

  if (( remaining <= 0 )); then
    echo "Target already reached: $current >= $target"
    return
  fi

  echo "Training from $current to at least $target ($remaining additional iterations)"
  "$PY" "$FS" train \
    -A "$TARGET_FACES" \
    -B "$SOURCE_FACES" \
    -m "$MODEL" \
    -t dlight \
    -b 4 \
    -i "$remaining" \
    -s 500 \
    -I 1000 \
    -w \
    -L INFO \
    -F "$LOG"
}

convert_test() {
  mkdir -p "$OUTPUT"
  "$PY" "$FS" convert \
    -i "$TARGET_FRAMES" \
    -p "$ALIGNMENTS" \
    -o "$OUTPUT" \
    -m "$MODEL" \
    -c avg-color \
    -M bisenet-fp_face \
    -w opencv \
    -R 1-120 \
    -a "$TARGET_FACES" \
    -j 1 \
    -P \
    -L INFO \
    -F "$ROOT/face-correction/work/output/p03-performer-dlight-v1-convert.log"
}

case "${1:-status}" in
  status)
    status
    ;;
  train-to)
    [[ $# -eq 2 ]] || { echo "Usage: $0 train-to TOTAL_ITERATIONS"; exit 2; }
    train_to "$2"
    ;;
  convert-test)
    convert_test
    ;;
  train-and-convert)
    [[ $# -eq 2 ]] || { echo "Usage: $0 train-and-convert TOTAL_ITERATIONS"; exit 2; }
    train_to "$2"
    convert_test
    ;;
  *)
    echo "Usage: $0 {status|train-to N|convert-test|train-and-convert N}"
    exit 2
    ;;
esac
