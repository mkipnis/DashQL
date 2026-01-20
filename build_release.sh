#!/usr/bin/env bash
set -euo pipefail

DEST="release"

mkdir -p "$DEST"

# Copy everything except dotfiles and the destination itself
rsync -a \
  --exclude='.*' \
  --exclude="$DEST" \
  ./ "$DEST/"

# Remove files that should not be in the release
rm -f \
  "$DEST/build_release.sh" \
  "$DEST/Dockerfile" \
  "$DEST/docker-compose.yml"
