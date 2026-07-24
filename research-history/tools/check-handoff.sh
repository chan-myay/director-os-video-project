#!/usr/bin/env bash

set -u

cd "$(dirname "$0")/.."

failed=0

check_file() {
  if [ -f "$1" ]; then
    echo "OK   $1"
  else
    echo "MISS $1"
    failed=1
  fi
}

check_file "RESUME.md"
check_file "RESEARCH.md"
check_file "output/PRODUCTION-FAILURE-AUDIT.md"
check_file "references/ASSET-STATUS.md"
check_file "audio/01.mp3"
check_file "pilot/selected/P03_performer-reveal_take01_SELECTED-BASE.mp4"
check_file "pilot/selected/edits/P03_SAFE-WIDE_00-00_to_00-02.5_v1.mp4"
check_file "references/approved/REF-A1_PERFORMER-FACE-FRONT_APPROVED.png"
check_file "references/approved/REF-A2_PERFORMER-FACE-THREEQUARTER_APPROVED.png"
check_file "references/approved/REF-B_PERFORMER-WARDROBE-FULLBODY_APPROVED.png"
check_file "wan-test/input/P03_FIRST-5S_MOTION-BACKGROUND.mp4"

source_count="$(find face-correction/source-lead performer -type f 2>/dev/null | wc -l | tr -d ' ')"
target_count="$(find face-correction/target-p03 -type f 2>/dev/null | wc -l | tr -d ' ')"

echo "INFO source-lead performer files: $source_count (expected 511)"
echo "INFO target-p03 frames: $target_count (expected 192)"

if [ "$source_count" -ne 511 ] || [ "$target_count" -ne 192 ]; then
  failed=1
fi

for tool in codex ffmpeg ssh; do
  if command -v "$tool" >/dev/null 2>&1; then
    echo "OK   tool: $tool"
  else
    echo "WARN tool not installed: $tool"
  fi
done

if [ "$failed" -ne 0 ]; then
  echo "HANDOFF CHECK FAILED"
  exit 1
fi

echo "HANDOFF CHECK PASSED"

