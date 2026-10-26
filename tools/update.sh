#!/bin/bash
# Update AdCamp Video System to a new version, keeping your reels, brand, music, styles and settings.
#   ~/AVS/tools/update.sh --latest                         the newest version, straight from GitHub
#   ~/AVS/tools/update.sh ~/Downloads/AVS-<version>.zip    a version you downloaded
#   ~/AVS/tools/update.sh <folder>                         an AVS folder (the plugin's, after a plugin update)
#   ~/AVS/tools/update.sh --check [--plugin <folder>]      is there a newer version? One line, no changes:
#       UPDATE NONE | UPDATE SKIPPED <why> | UPDATE SYNC <folder> | UPDATE AVAILABLE <old> -> <new>: <what's new>
#     GitHub is asked at most once a day (runtime/update-check.json). With --plugin, a plugin that is newer
#     than ~/AVS comes first: SYNC means "copy it in", no download.
set -euo pipefail
RE="$(cd "$(dirname "$0")/.." && pwd)"
REPO="${AVS_REPO:-https://github.com/Distinguished-Creative-Co/adcamp-video-system}"
RAW="${AVS_REPO_RAW:-https://raw.githubusercontent.com/Distinguished-Creative-Co/adcamp-video-system/main}"
TARBALL="${AVS_REPO_TARBALL:-$REPO/archive/refs/heads/main.tar.gz}"
SRC="${1:?usage: tools/update.sh --latest | --check [--plugin <folder>] | <AVS-x.y.z.zip> | <AVS folder>}"
OLD="$(cat "$RE/VERSION" 2>/dev/null || echo 0.0.0)"

newer(){ # newer A B: is version A newer than B?
  [ "$1" != "$2" ] && [ "$(printf '%s\n%s\n' "$1" "$2" | sort -t. -k1,1n -k2,2n -k3,3n | tail -1)" = "$1" ]
}

if [ "$SRC" = "--check" ]; then
  PLUGIN=""; [ "${2:-}" = "--plugin" ] && PLUGIN="${3:-}"
  if [ -n "$PLUGIN" ] && [ -f "$PLUGIN/VERSION" ] && newer "$(cat "$PLUGIN/VERSION")" "$OLD"; then
    echo "UPDATE SYNC $PLUGIN"; exit 0
  fi
  CACHE="$RE/runtime/update-check.json"; TODAY="$(date +%F)"
  if [ -f "$CACHE" ] && grep -q "\"checked\": \"$TODAY\"" "$CACHE"; then
    NEW="$(sed -n 's/.*"newest": "\([^"]*\)".*/\1/p' "$CACHE")"; NOTE="$(sed -n 's/.*"note": "\([^"]*\)".*/\1/p' "$CACHE")"
  else
    NEW="$(curl -fsSL --max-time 8 "$RAW/VERSION" 2>/dev/null | tr -d '[:space:]')" || NEW=""
    [ -n "$NEW" ] || { echo "UPDATE SKIPPED (could not reach GitHub)"; exit 0; }
    NOTE="$(curl -fsSL --max-time 8 "$RAW/whats-new.json" 2>/dev/null | "$RE/runtime/bin/python3" -c "import json,sys; print(json.load(sys.stdin).get(sys.argv[1],'fixes and improvements'))" "$NEW" 2>/dev/null)" || NOTE=""   # AVS's own Python: a bare python3 on a Mac can pop the developer-tools dialog
    NOTE="${NOTE:-fixes and improvements}"; NOTE="${NOTE//\"/\'}"
    mkdir -p "$RE/runtime"
    printf '{"checked": "%s", "newest": "%s", "note": "%s"}\n' "$TODAY" "$NEW" "$NOTE" > "$CACHE"
  fi
  if newer "$NEW" "$OLD"; then echo "UPDATE AVAILABLE $OLD -> $NEW: $NOTE"; else echo "UPDATE NONE ($OLD is the newest)"; fi
  exit 0
fi

[ "$SRC" = "--latest" ] || [ -e "$SRC" ] || { echo "no such file or folder: $SRC"; exit 1; }
ENG="$RE/engine"
BK="$(mktemp -d)"
echo "Backing up your settings to $BK"
cp "$ENG/src/brand.json" "$ENG/sounds.json" "$BK/" 2>/dev/null || true
[ -d "$ENG/sounds/music" ] && cp -R "$ENG/sounds/music" "$BK/music"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT   # the unpacked package copy never stays behind
if [ "$SRC" = "--latest" ]; then
  echo "Downloading the newest AVS from GitHub (about 50 MB)"
  mkdir -p "$TMP/AVS"
  curl -fsSL "$TARBALL" | tar -xz -C "$TMP/AVS" --strip-components 1 || { echo "download failed: check your internet connection"; exit 1; }
elif [ -d "$SRC" ]; then
  mkdir -p "$TMP/AVS"
  rsync -a --exclude '.git' "$SRC/" "$TMP/AVS/"
else
  ditto -x -k "$SRC" "$TMP"
fi
[ -d "$TMP/AVS/engine" ] || { echo "that is not an AVS package"; exit 1; }
NEW="$(cat "$TMP/AVS/VERSION")"
# code and docs only: reels, inputs, renders, qa, styles, picks and runtime are never in the package
rsync -a --checksum --exclude 'engine/src/methodology/reels/' --exclude '.claude-plugin' "$TMP/AVS/" "$RE/"   # by content: a same-size edit with a close timestamp must still land
chmod +x "$RE/install.sh" "$RE"/tools/*.sh "$ENG/scripts/make_reel.sh"
cp "$BK/brand.json" "$BK/sounds.json" "$ENG/" 2>/dev/null || true
mv "$ENG/brand.json" "$ENG/src/brand.json" 2>/dev/null || true
[ -d "$BK/music" ] && cp -R "$BK/music/." "$ENG/sounds/music/"
rm -f "$RE/runtime/update-check.json"
[ -d "$SRC" ] && [ -f "$RE/runtime/.via-plugin" ] && echo "$(cd "$SRC" && pwd)" > "$RE/runtime/.via-plugin"   # the plugin moved to its new version folder
. "$RE/runtime/env.sh"
cd "$ENG"
for c in src/methodology/reels/*.config.ts; do
  [ -f "$c" ] || continue
  n="$(basename "$c" .config.ts)"
  python3 -c "import sys; sys.path.insert(0,'scripts'); import gen_reel_config as g; g.register('$n', False)" >/dev/null 2>&1 || true
done
"$RE/install.sh" --step npm
"$RE/install.sh" --step cutout
"$RE/install.sh" --step ytdlp
"$RE/install.sh" --step skill

# Installed from the Plugins panel and updated from GitHub: bring the plugin (the skill) along too.
if [ -f "$RE/runtime/.via-plugin" ] && [ "$SRC" = "--latest" ]; then
  CL=""
  for c in "${CLAUDE_CODE_EXECPATH:-}" "$(command -v claude 2>/dev/null || true)" "$HOME/.claude/local/claude" \
           "$HOME/.local/bin/claude" /usr/local/bin/claude /opt/homebrew/bin/claude; do
    [ -n "$c" ] && [ -x "$c" ] && { CL="$c"; break; }
  done
  if [ -n "$CL" ] && "$CL" plugin marketplace update adcamp >/dev/null 2>&1 && "$CL" plugin update avs@adcamp >/dev/null 2>&1; then
    echo "The AVS plugin is updated too."
  else
    echo "One more step for the plugin: open Plugins, then Manage plugins, and update AVS (or in a terminal: claude plugin update avs@adcamp)."
  fi
fi
touch "$RE/runtime/.installed"   # an install that updates is a finished install
rm -rf "$BK"   # the settings backup is only needed if the update stops partway
echo "Updated AVS $OLD -> $NEW. Your reels, brand, music and styles are kept."
