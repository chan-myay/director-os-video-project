#!/usr/bin/env zsh
set -euo pipefail

# Draft only. Do not run until the user explicitly approves rendering v2C.
# This script uses existing selected clips and audio only.
# It refuses to overwrite an existing output. If a prior interrupted run created
# some segments, it skips those segments and completes the missing ones.

ROOT="/Users/chan/song-video-project"
EDL="$ROOT/director-os-audit/phase-2-v2c/V2C_SAFE_EDL.csv"
WORK="$ROOT/production/edit/roughcut-v2"
SEGMENTS="$WORK/segments-v2c-safe-local-recut"
CONCAT="$WORK/concat-v2c-safe-local-recut.txt"
OUT="$WORK/ROUGH-CUT-V2C_SAFE-LOCAL-RECUT_WITH-MP3.mp4"
AUDIO="$ROOT/audio/01.mp3"
FFMPEG="$ROOT/local-tools/envs/faceswap/bin/ffmpeg"
FFPROBE="$ROOT/local-tools/envs/faceswap/lib/python3.13/site-packages/ffmpeg/binaries/ffprobe"

if [[ ! -f "$EDL" ]]; then
  echo "Missing EDL: $EDL" >&2
  exit 1
fi

if [[ -e "$OUT" ]]; then
  echo "Refusing to overwrite existing output: $OUT" >&2
  exit 1
fi

mkdir -p "$SEGMENTS"
touch "$CONCAT"

line_no=0
while IFS=, read -r order start_time end_time song_section clip_path in_point out_point reason face_action_needed body_risk use_status notes; do
  line_no=$((line_no + 1))
  src="$ROOT/$clip_path"
  if [[ ! -f "$src" ]]; then
    echo "Missing clip for EDL row $order: $clip_path" >&2
    exit 1
  fi

  n=$(printf "%03d" "$order")
  dst="$SEGMENTS/$n.mp4"
  echo "[$n] $clip_path $in_point -> $out_point"

  if [[ ! -f "$dst" ]]; then
    "$FFMPEG" -n -v error -i "$src" \
      -ss "$in_point" -to "$out_point" \
      -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=24,format=yuv420p" \
      -an -c:v libx264 -preset veryfast -crf 18 "$dst" </dev/null
  fi

  if ! grep -Fq "$dst" "$CONCAT"; then
    printf "file '%s'\n" "$dst" >> "$CONCAT"
  fi
done < <(tail -n +2 "$EDL")

audio_duration=$("$FFPROBE" -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$AUDIO")
echo "Audio duration: $audio_duration"

"$FFMPEG" -n -v error -f concat -safe 0 -i "$CONCAT" -i "$AUDIO" \
  -map 0:v:0 -map 1:a:0 -t "$audio_duration" \
  -c:v libx264 -preset veryfast -crf 18 -pix_fmt yuv420p \
  -c:a aac -b:a 320k -movflags +faststart "$OUT"

echo "Draft render complete: $OUT"
"$FFPROBE" -v error -show_entries format=duration,size -of default=noprint_wrappers=1 "$OUT"
