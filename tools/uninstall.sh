#!/bin/bash
# Remove Distinguished Vertical Editor: the ~/DVE folder (runtime, engine, your reels) and the Claude Code
# skill. Your finished videos in engine/out are copied to ~/Desktop/DVE-videos first
# unless you pass --delete-videos. Nothing outside these two places was ever installed.
#   ~/DVE/tools/uninstall.sh [--yes] [--delete-videos]
set -euo pipefail
RE="$(cd "$(dirname "$0")/.." && pwd)"
YES=0; KEEP=1
for a in "$@"; do case "$a" in --yes) YES=1;; --delete-videos) KEEP=0;; esac; done
echo "This removes $RE ($(du -sh "$RE" 2>/dev/null | cut -f1)) and ~/.claude/skills/dve."
[ "$KEEP" -eq 1 ] && echo "Finished videos in engine/out will be copied to ~/Desktop/DVE-videos first."
if [ "$YES" -ne 1 ]; then read -r -p "Type REMOVE to continue: " ans; [ "$ans" = "REMOVE" ] || { echo "Cancelled."; exit 1; }; fi
if [ "$KEEP" -eq 1 ] && ls "$RE/engine/out/"*.mp4 >/dev/null 2>&1; then
  mkdir -p "$HOME/Desktop/DVE-videos"; cp -R "$RE/engine/out/." "$HOME/Desktop/DVE-videos/"
  echo "Videos copied to ~/Desktop/DVE-videos"
fi
rm -rf "$HOME/.claude/skills/dve"
rm -rf "$RE"
echo "DVE removed."
