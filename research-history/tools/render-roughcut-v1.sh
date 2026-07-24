#!/usr/bin/env zsh
set -euo pipefail

ROOT="/Users/chan/song-video-project"
FFMPEG="$ROOT/local-tools/envs/faceswap/bin/ffmpeg"
FFPROBE="$ROOT/local-tools/envs/faceswap/lib/python3.13/site-packages/ffmpeg/binaries/ffprobe"
WORK="$ROOT/production/edit/roughcut-v1"
SEGMENTS="$WORK/segments"
CONCAT="$WORK/concat-normalized.txt"
OUT="$WORK/ROUGH-CUT-V1_WITH-MP3.mp4"
AUDIO="$ROOT/audio/01.mp3"

mkdir -p "$SEGMENTS"
rm -f "$CONCAT"

typeset -a CLIPS
CLIPS=(
  "production/selected/batch-a/A01_winter-exterior_SELECTED.mp4"
  "production/selected/batch-a/A02_empty-bar_SELECTED.mp4"
  "production/selected/batch-a/A03_two-glasses_SELECTED.mp4"
  "production/selected/batch-a/A04_empty-chair_SELECTED.mp4"
  "pilot/selected/P03_FINAL-SELECTED_FULL-HIFIFACE256_v1.mp4"
  "production/selected/batch-c/C01_verse1-stable-medium_SELECTED.mp4"
  "production/selected/batch-c/C02_verse1-frontal-close_SELECTED.mp4"
  "production/selected/batch-a/A05_rose-macro_SELECTED.mp4"
  "production/selected/batch-c/C03_verse1-threequarter-emotion_SELECTED.mp4"
  "production/selected/batch-b/B02_weight-shift-wrist_SELECTED.mp4"
  "production/selected/batch-a/A07_burmese-craft_SELECTED.mp4"
  "production/selected/batch-c/C04_pre-chorus-hand-heart_SELECTED.mp4"
  "production/selected/batch-a/A03_two-glasses_SELECTED.mp4"
  "production/selected/batch-c/C06_chorus-silent-emotional-hold_SELECTED.mp4"
  "production/selected/batch-b/B03_curtain-silhouette_SELECTED.mp4"
  "production/selected/batch-c/C05_chorus-emotional-front_SELECTED.mp4"
  "production/selected/batch-c/C08_tearful-close-eye-detail_SELECTED.mp4"
  "production/selected/batch-a/A08_snow-window_SELECTED.mp4"
  "production/selected/batch-c/C02_verse1-frontal-close_SELECTED.mp4"
  "production/selected/batch-c/C09_chorus-performance-wide_SELECTED-stage-continuity-face-caution.mp4"
  "production/selected/batch-a/A07_burmese-craft_SELECTED.mp4"
  "production/selected/batch-c/C03_verse1-threequarter-emotion_SELECTED.mp4"
  "production/selected/batch-a/A09_door-bolt_SELECTED-reversed-to-lock.mp4"
  "production/selected/batch-c/C01_verse1-stable-medium_SELECTED.mp4"
  "production/selected/batch-b/B04_aisle-travel-a_SELECTED.mp4"
  "production/selected/batch-b/B05_aisle-travel-b_SELECTED.mp4"
  "production/selected/batch-c/C07_profile-memory-look_SELECTED_use-after-00-02.mp4"
  "production/selected/batch-c/C04_pre-chorus-hand-heart_SELECTED.mp4"
  "production/selected/batch-a/A03_two-glasses_SELECTED.mp4"
  "production/selected/batch-b/B06_return-to-stage_SELECTED.mp4"
  "production/selected/batch-c/C10_final-still-resolve_SELECTED.mp4"
  "production/selected/batch-b/B07_rose-placement_SELECTED.mp4"
  "production/selected/batch-b/B08_curtain-exit_SELECTED-TRIM-BEFORE-CLOSE.mp4"
  "production/selected/batch-c/C06_chorus-silent-emotional-hold_SELECTED.mp4"
  "production/selected/batch-c/C08_tearful-close-eye-detail_SELECTED.mp4"
  "production/selected/batch-a/A05_rose-macro_SELECTED.mp4"
  "production/selected/batch-a/A10_empty-microphone_SELECTED.mp4"
)

echo "Rough cut v1 render"
echo "Clips: ${#CLIPS[@]}"
echo "Output: $OUT"

i=1
for clip in "${CLIPS[@]}"; do
  src="$ROOT/$clip"
  if [[ ! -f "$src" ]]; then
    echo "Missing clip: $clip" >&2
    exit 1
  fi
  n=$(printf "%03d" "$i")
  dst="$SEGMENTS/$n.mp4"
  echo "[$n/${#CLIPS[@]}] normalize $clip"
  "$FFMPEG" -y -v error -i "$src" \
    -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=24,format=yuv420p" \
    -an -c:v libx264 -preset veryfast -crf 18 "$dst"
  echo "file '$dst'" >> "$CONCAT"
  i=$((i + 1))
done

audio_duration=$("$FFPROBE" -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$AUDIO")
echo "Audio duration: $audio_duration"
echo "Concatenate and mux MP3 master"
"$FFMPEG" -y -v error -f concat -safe 0 -i "$CONCAT" -i "$AUDIO" \
  -map 0:v:0 -map 1:a:0 -t "$audio_duration" \
  -c:v libx264 -preset veryfast -crf 18 -pix_fmt yuv420p \
  -c:a aac -b:a 320k -movflags +faststart "$OUT"

echo "Done"
"$FFPROBE" -v error -show_entries format=duration,size -of default=noprint_wrappers=1 "$OUT"
