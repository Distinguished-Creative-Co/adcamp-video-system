#!/bin/bash
# Distinguished Vertical Editor install test: builds the included sample clip and renders it in Studio, Minimal
# and Hype. Takes about 5-15 minutes (longer on Intel). Safe to run again.
#   ~/DVE/tools/smoke_test.sh
# The sample is a real reel its owner already approved, so this test approves its own previews.
# Your own reels always wait for YOUR approval.
set -euo pipefail
RE="$(cd "$(dirname "$0")/.." && pwd)"
ENG="$RE/engine"
[ -f "$RE/runtime/env.sh" ] || { echo "error: DVE is not installed. Run ~/DVE/install.sh"; exit 1; }
. "$RE/runtime/env.sh"
cd "$ENG"
RAW="samples/sample.mp4"
say(){ printf '\n\033[1;36m== %s\033[0m\n' "$*"; }
ready(){ grep -q '^\*\*Status: READY' "script/$1-scene-map.md" || { echo "error: the $1 preview is not ready, see script/$1-scene-map.md"; exit 1; }; }
start=$(date +%s)

say "1/4  Studio: cut the sample (keeps the last clean take of each line) and build the preview"
cp samples/sample.txt script/sample.txt
cp samples/sample-trims.json script/word-timings/sample-trims.json
scripts/make_reel.sh "$RAW" sample --face 610,880 --preview
echo "(Expected on this first pass: a seam FAIL after \"a single ad.\" and NOT READY. The next step fills the sample's copy and clears both.)"
python3 samples/fill_sample.py
python3 scripts/verify_seams.py sample
scripts/make_reel.sh "$RAW" sample --preview
ready sample

say "2/4  Studio: render"
python3 scripts/approve_reel.py sample --by "install test (sample clip)"
scripts/make_reel.sh "$RAW" sample --render

for st in minimal hype; do
  n="sample-$st"
  say "$([ $st = minimal ] && echo 3 || echo 4)/4  $(echo $st | awk '{print toupper(substr($0,1,1)) substr($0,2)}'): preview and render"
  python3 scripts/make_style.py sample "$st" --force
  "$DVE_MATTE_PYTHON" scripts/matte_reel.py "$n"
  python3 scripts/scene_map.py "$n"
  node scripts/test_layout.mjs "$n"
  ready "$n"
  python3 scripts/approve_reel.py "$n" --by "install test (sample clip)"
  scripts/make_reel.sh "$RAW" "$n" --render
done

mins=$(( ($(date +%s) - start + 59) / 60 ))
printf '\n\033[1;32mInstall test passed in about %d min.\033[0m Three videos are in %s/out:\n' "$mins" "$ENG"
for n in sample sample-minimal sample-hype; do printf '  %s.mp4\n' "$n"; done
echo "Open the folder: open \"$ENG/out\""
