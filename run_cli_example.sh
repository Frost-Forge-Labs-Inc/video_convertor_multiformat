#!/usr/bin/env bash
set -euo pipefail

python3 -m video_convertor_multiformat.cli \
  --input "./input" \
  --output "./output" \
  --formats "mp4,mp3,wav" \
  --crf 18 \
  --preset slow \
  --audio-bitrate 192k \
  --verbose
