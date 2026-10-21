#!/bin/bash
# Update Distinguished Vertical Editor to a new version, keeping your reels, brand, music and settings.
#   ~/DVE/tools/update.sh --latest                         the newest version, straight from GitHub
#   ~/DVE/tools/update.sh ~/Downloads/DVE-<version>.zip    a version you downloaded
set -euo pipefail
RE="$(cd "$(dirname "$0")/.." && pwd)"
ZIP="${1:?usage: tools/update.sh --latest | <DVE-x.y.z.zip>}"
[ "$ZIP" = "--latest" ] || [ -f "$ZIP" ] || { echo "no such file: $ZIP"; exit 1; }
ENG="$RE/engine"
BK="$(mktemp -d)"
echo "Backing up your settings to $BK"
cp "$ENG/src/brand.json" "$ENG/sounds.json" "$BK/" 2>/dev/null || true
[ -d "$ENG/sounds/music" ] && cp -R "$ENG/sounds/music" "$BK/music"
TMP="$(mktemp -d)"
if [ "$ZIP" = "--latest" ]; then
  echo "Downloading the newest DVE from GitHub (about 50 MB)"
  curl -fsSL "https://github.com/Distinguished-Creative-Co/dve/archive/refs/heads/main.tar.gz" | tar -xz -C "$TMP" || { echo "download failed: check your internet connection"; exit 1; }
  mv "$TMP"/dve-main "$TMP/DVE"
else
  ditto -x -k "$ZIP" "$TMP"
fi
[ -d "$TMP/DVE/engine" ] || { echo "that zip is not a DVE package"; exit 1; }
OLD="$(cat "$RE/VERSION" 2>/dev/null || echo '?')"; NEW="$(cat "$TMP/DVE/VERSION")"
# code and docs only: reels, inputs, renders, qa, scripts of yours, runtime are never in the zip
rsync -a --exclude 'engine/src/methodology/reels/' "$TMP/DVE/" "$RE/"
cp "$BK/brand.json" "$BK/sounds.json" "$ENG/" 2>/dev/null || true
mv "$ENG/brand.json" "$ENG/src/brand.json" 2>/dev/null || true
[ -d "$BK/music" ] && cp -R "$BK/music/." "$ENG/sounds/music/"
. "$RE/runtime/env.sh"
cd "$ENG"
for c in src/methodology/reels/*.config.ts; do
  [ -f "$c" ] || continue
  n="$(basename "$c" .config.ts)"
  python3 -c "import sys; sys.path.insert(0,'scripts'); import gen_reel_config as g; g.register('$n', False)" >/dev/null 2>&1 || true
done
"$RE/install.sh" --step npm
"$RE/install.sh" --step cutout
"$RE/install.sh" --step skill
echo "Updated DVE $OLD -> $NEW. Your reels, brand and music are kept."
