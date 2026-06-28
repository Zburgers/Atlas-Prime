#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
OUT_DIR="$ROOT_DIR/fixtures/media"
OUT_FILE="$OUT_DIR/sample-2s.mp4"

mkdir -p "$OUT_DIR"

ffmpeg -y \
  -f lavfi -i testsrc=size=640x360:rate=24 \
  -f lavfi -i sine=frequency=1000:sample_rate=48000 \
  -t 2 \
  -c:v libx264 -pix_fmt yuv420p \
  -c:a aac -b:a 96k \
  -movflags +faststart \
  "$OUT_FILE"

printf 'Generated %s\n' "$OUT_FILE"
