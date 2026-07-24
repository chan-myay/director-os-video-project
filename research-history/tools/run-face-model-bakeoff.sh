#!/bin/zsh

set -u

ROOT="/Users/chan/song-video-project"
FF="$ROOT/local-tools/facefusion"
PY="$ROOT/local-tools/envs/facefusion/bin/python"
SOURCE="$ROOT/face-correction/model-bakeoff/source/IMG_6706_at-05s.jpg"
TARGET="$ROOT/pilot/selected/P03_performer-reveal_take01_SELECTED-BASE.mp4"
OUT="$ROOT/face-correction/model-bakeoff/videos"
LOG="$ROOT/face-correction/model-bakeoff/logs"
PROGRESS="$ROOT/face-correction/model-bakeoff/PROGRESS.md"
PATH="$ROOT/local-tools/envs/facefusion/bin:$ROOT/local-tools/envs/faceswap/bin:/usr/bin:/bin:/usr/sbin:/sbin"

models=(
  "01 blendswap_256 512x512"
  "02 ghost_1_256 512x512"
  "03 ghost_2_256 512x512"
  "04 ghost_3_256 512x512"
  "05 hififace_unofficial_256 512x512"
  "06 hyperswap_1a_256 512x512"
  "07 hyperswap_1b_256 512x512"
  "08 hyperswap_1c_256 512x512"
  "09 inswapper_128 512x512"
  "10 inswapper_128_fp16 512x512"
  "11 simswap_256 512x512"
  "12 simswap_unofficial_512 512x512"
  "13 uniface_256 512x512"
)

mkdir -p "$OUT" "$LOG"

write_progress() {
  local current="$1"
  local run_state="$2"
  local completed
  local failed
  completed=$(find "$OUT" -maxdepth 1 -name '*.mp4' | wc -l | tr -d ' ')
  failed=$(find "$LOG" -maxdepth 1 -name '*.failed' | wc -l | tr -d ' ')
  {
    echo "# Local Face Model Bake-off"
    echo
    echo "- Updated: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "- Current: $current"
    echo "- Status: $run_state"
    echo "- Preserved videos: $completed"
    echo "- Failed model attempts: $failed"
    echo "- Total candidates: 14 including original Gemini"
  } > "$PROGRESS"
}

write_progress "setup" "running"

cd "$FF" || exit 1

for spec in "${models[@]}"; do
  parts=(${=spec})
  index="${parts[1]}"
  model="${parts[2]}"
  boost="${parts[3]}"
  output="$OUT/${index}_${model}.mp4"
  logfile="$LOG/${index}_${model}.log"

  if [[ -s "$output" ]]; then
    write_progress "$model" "already preserved; skipped"
    continue
  fi

  write_progress "$model" "rendering full 8-second shot"

  "$PY" facefusion.py headless-run \
    -s "$SOURCE" \
    -t "$TARGET" \
    -o "$output" \
    --processors face_swapper \
    --face-swapper-model "$model" \
    --face-swapper-pixel-boost "$boost" \
    --face-swapper-weight 1.0 \
    --face-selector-mode one \
    --face-detector-model retinaface \
    --face-mask-types box region \
    --face-mask-regions skin left-eyebrow right-eyebrow left-eye right-eye nose mouth upper-lip lower-lip \
    --face-mask-blur 0.2 \
    --temp-frame-format png \
    --output-video-encoder libx264 \
    --output-video-quality 95 \
    --output-video-preset fast \
    --execution-providers cpu \
    --execution-thread-count 4 \
    --video-memory-strategy strict \
    --log-level info > "$logfile" 2>&1

  if [[ $? -ne 0 || ! -s "$output" ]]; then
    touch "$LOG/${index}_${model}.failed"
    write_progress "$model" "failed; evidence log preserved"
  else
    write_progress "$model" "completed"
  fi
done

write_progress "all models" "complete"
