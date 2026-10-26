#!/bin/bash
# First run after installing AVS from the Claude Code Plugins panel: copy it into ~/AVS.
#   bash <plugin root>/tools/plugin_setup.sh
#
# The plugin folder Claude Code installs is read-only and replaced on every update, so AVS never works
# inside it. ~/AVS is where reels, footage, the brand and the downloaded tools live. This copies the
# engine and the installer there (no download) and marks the install as plugin-managed, so the skill
# comes from the plugin instead of ~/.claude/skills. Then INSTALL.md takes over.
set -euo pipefail
SRC="$(cd "$(dirname "$0")/.." && pwd)"
DST="$HOME/AVS"
[ -f "$SRC/VERSION" ] && [ -d "$SRC/engine" ] || { echo "plugin_setup: $SRC is not an AVS plugin folder"; exit 1; }
if [ -f "$DST/runtime/env.sh" ]; then
  echo "AVS is already set up in ~/AVS. To bring it to this version: ~/AVS/tools/update.sh \"$SRC\""
  exit 0
fi
if [ -e "$DST" ] && [ ! -d "$DST/engine" ]; then
  echo "plugin_setup: ~/AVS exists but is not AVS. Move or rename it, then run this again."
  exit 1
fi
mkdir -p "$DST"
rsync -a --exclude '.git' --exclude '.claude-plugin' "$SRC/" "$DST/"
mkdir -p "$DST/runtime"
echo "$SRC" > "$DST/runtime/.via-plugin"
chmod +x "$DST/install.sh" "$DST"/tools/*.sh "$DST/engine/scripts/make_reel.sh"
echo "AVS $(cat "$DST/VERSION") copied to ~/AVS. Next: follow ~/AVS/INSTALL.md (the skill comes from the plugin)."
