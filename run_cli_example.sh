#!/usr/bin/env bash
set -euo pipefail

python -m video_to_mp4_converter.cli \
  --input "./input" \
  --output "./output" \
  --formats "mp4,mp3,wav" \
  --crf 18 \
  --preset slow \
  --audio-bitrate 192k \
  --verbose
