#!/bin/bash
# Remove AdCamp Video System: the ~/AVS folder (runtime, engine, your reels) and the Claude Code
# skill. Your finished videos in engine/out are copied to ~/Desktop/AVS-videos first
# unless you pass --delete-videos. Nothing outside these two places was ever installed.
#   ~/AVS/tools/uninstall.sh [--yes] [--delete-videos]
set -euo pipefail
RE="$(cd "$(dirname "$0")/.." && pwd)"
YES=0; KEEP=1
for a in "$@"; do case "$a" in --yes) YES=1;; --delete-videos) KEEP=0;; esac; done
echo "This removes $RE ($(du -sh "$RE" 2>/dev/null | cut -f1)) and ~/.claude/skills/avs."
[ "$KEEP" -eq 1 ] && echo "Your inbox footage, scripts and saved styles go with it. Finished videos and carousel slides are copied to ~/Desktop/AVS-videos first."
if [ "$YES" -ne 1 ]; then read -r -p "Type REMOVE to continue: " ans; [ "$ans" = "REMOVE" ] || { echo "Cancelled."; exit 1; }; fi
if [ "$KEEP" -eq 1 ] && ls "$RE/engine/out/"*.mp4 >/dev/null 2>&1; then
  mkdir -p "$HOME/Desktop/AVS-videos"; rsync -a --exclude 'drafts/' --exclude '.*' --exclude 'sample.mp4' --exclude 'sample-phone.mp4' --exclude 'sample-companions/' \
    --exclude 'font-sheet.png' "$RE/engine/out/" "$HOME/Desktop/AVS-videos/"   # their finished videos: never the drafts or the install test's
  for f in "$RE/engine/script/"*-post*.md "$RE/engine/script/"*-ad.md; do   # the caption and ad copy drafts, each on its own
    [ -f "$f" ] || continue
    case "$(basename "$f")" in sample-post*) continue;; esac   # the install test's caption
    mkdir -p "$HOME/Desktop/AVS-videos/captions"; cp "$f" "$HOME/Desktop/AVS-videos/captions/"
  done
  if [ -n "$(ls -A "$HOME/Desktop/AVS-videos" 2>/dev/null)" ]; then echo "Videos copied to ~/Desktop/AVS-videos"
  else rmdir "$HOME/Desktop/AVS-videos" 2>/dev/null; echo "No finished videos of yours to copy."; fi   # only the install test's were there
fi
if [ "$KEEP" -eq 1 ] && ls "$RE/engine/carousels/"*/slides/*.png >/dev/null 2>&1; then
  for d in "$RE/engine/carousels/"*/; do
    [ -d "$d/slides" ] || continue
    mkdir -p "$HOME/Desktop/AVS-videos/carousels/$(basename "$d")"; cp -R "$d/slides/." "$HOME/Desktop/AVS-videos/carousels/$(basename "$d")/"
    [ -f "$d/carousel.json" ] && [ -x "$RE/runtime/bin/python3" ] && "$RE/runtime/bin/python3" -c "import json,sys; print(json.load(open(sys.argv[1])).get('caption') or '')" "$d/carousel.json" \
      > "$HOME/Desktop/AVS-videos/carousels/$(basename "$d")/caption.txt" 2>/dev/null || true   # the post caption too
  done
  echo "Carousel slides copied to ~/Desktop/AVS-videos/carousels"
fi
rm -rf "$HOME/.claude/skills/avs"
rm -rf "$RE"
echo "AVS removed. If you installed it from the Plugins panel, remove AdCamp Video System there too."
