#!/usr/bin/env bash
# Compress assets/icons to low-weight 64x64 PNGs (requires pngquant).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
find assets/icons -name '*.png' -print0 | xargs -0 -P 8 -I{} \
  pngquant --quality=40-70 --speed 1 --force --skip-if-larger --ext .png {}
du -sh assets/icons
