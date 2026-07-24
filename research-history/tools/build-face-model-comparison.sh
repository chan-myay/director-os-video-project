#!/bin/zsh

set -e

ROOT="/Users/chan/song-video-project"
FFMPEG="$ROOT/local-tools/envs/faceswap/bin/ffmpeg"
IN="$ROOT/face-correction/model-bakeoff/videos"
OUT="$ROOT/face-correction/model-bakeoff/FACE-MODEL-COMPARISON-ALL-14.mp4"
FONT="/System/Library/Fonts/Supplemental/Arial Bold.ttf"

files=(
  "00_ORIGINAL-GEMINI.mp4"
  "01_blendswap_256.mp4"
  "02_ghost_1_256.mp4"
  "03_ghost_2_256.mp4"
  "04_ghost_3_256.mp4"
  "05_hififace_unofficial_256.mp4"
  "06_hyperswap_1a_256.mp4"
  "07_hyperswap_1b_256.mp4"
  "08_hyperswap_1c_256.mp4"
  "09_inswapper_128.mp4"
  "10_inswapper_128_fp16.mp4"
  "11_simswap_256.mp4"
  "12_simswap_unofficial_512.mp4"
  "13_uniface_256.mp4"
)

labels=(
  "00 ORIGINAL GEMINI"
  "01 BLENDSWAP 256"
  "02 GHOST 1 256"
  "03 GHOST 2 256"
  "04 GHOST 3 256"
  "05 HIFIFACE 256"
  "06 HYPERSWAP 1A"
  "07 HYPERSWAP 1B"
  "08 HYPERSWAP 1C"
  "09 INSWAPPER 128"
  "10 INSWAPPER 128 FP16"
  "11 SIMSWAP 256"
  "12 SIMSWAP 512"
  "13 UNIFACE 256"
)

args=()
filters=()
streams=""

for index in {1..14}; do
  array_index=$((index - 1))
  args+=(-i "$IN/${files[$index]}")
  filters+=(
    "[$array_index:v]drawtext=fontfile='${FONT}':text='${labels[$index]}':fontcolor=white:fontsize=32:box=1:boxcolor=black@0.72:boxborderw=14:x=28:y=28,format=yuv420p[v$array_index]"
  )
  streams+="[v${array_index}][${array_index}:a]"
done

filter_graph="${(j:;:)filters};${streams}concat=n=14:v=1:a=1[v][a]"

"$FFMPEG" -hide_banner -loglevel warning -y \
  "${args[@]}" \
  -filter_complex "$filter_graph" \
  -map "[v]" -map "[a]" \
  -c:v libx264 -preset fast -crf 17 \
  -c:a aac -b:a 256k \
  -movflags +faststart \
  "$OUT"

echo "$OUT"
