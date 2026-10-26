#!/bin/bash
# AdCamp Video System install test: builds the included sample clip in the Clean Talk starter look and renders it,
# previews it in a second look (Big Energy), then checks the tools (draft, saved styles, the Picker, carousels,
# joined clips, beat versions, the pages beside the chat). Takes 10 to 15 minutes (longer on Intel). Safe to run again.
#   ~/AVS/tools/smoke_test.sh
# The sample is a real reel its owner already approved, so this test approves its own previews.
# Your own reels always wait for YOUR approval.
set -euo pipefail
RE="$(cd "$(dirname "$0")/.." && pwd)"
ENG="$RE/engine"
[ -f "$RE/runtime/env.sh" ] || { echo "error: AVS is not installed. Run ~/AVS/install.sh"; exit 1; }
. "$RE/runtime/env.sh"
cd "$ENG"
RAW="samples/sample.mp4"
say(){ printf '\n\033[1;36m== %s\033[0m\n' "$*"; }
ready(){ grep -q '^\*\*Status: READY' "script/$1-scene-map.md" || { echo "error: the $1 preview is not ready, see script/$1-scene-map.md"; exit 1; }; }
start=$(date +%s)

say "1/4  Your test video: cut the sample (keeps the last clean take of each line), in the Clean Talk look"
cp samples/sample.txt script/sample.txt
cp samples/sample-trims.json script/word-timings/sample-trims.json
# --regen: always a fresh config, so a sample from an older version (or an interrupted run) is never reused
scripts/make_reel.sh "$RAW" sample --face 510,760 --outdoor --regen --preview
echo "(Expected on this first pass: NOT READY, the copy is blank and a few breaths between takes are flagged. The next steps set the look, fill the copy and sign off those breaths.)"
python3 scripts/make_style.py sample clean-talk --in-place --force
python3 samples/fill_sample.py
python3 scripts/verify_seams.py sample
scripts/make_reel.sh "$RAW" sample --outdoor --preview
ready sample

say "2/4  Render it"
python3 scripts/approve_reel.py sample --by "install test (sample clip)"
rm -f out/sample.mp4 out/sample-v*.mp4   # the test's own video: a re-run replaces it instead of adding a version
scripts/make_reel.sh "$RAW" sample --render

say "3/4  A second look from the same take: Big Energy (preview only)"
python3 scripts/make_style.py sample big-energy --force
"$AVS_MATTE_PYTHON" scripts/matte_reel.py sample-big-energy
python3 scripts/scene_map.py sample-big-energy
node scripts/test_layout.mjs sample-big-energy
ready sample-big-energy
python3 scripts/extract_reel_stills.py sample-big-energy --preview >/dev/null
# a second version takes on its own look, never the first one's: Soft Story has no hook title and its own transition
python3 scripts/make_style.py sample soft-story --force >/dev/null
python3 - <<'PY'
import sys
sys.path.insert(0, 'scripts')
import reel_config
c = reel_config.load('sample-soft-story')
tr = {e['style'] for e in c.get('effects', []) if e['kind'] == 'transition'}
if c.get('backText') or not tr or tr - {'iris'}:
    sys.exit('error: the Soft Story version kept the Clean Talk look (transitions %s, hook title %s)' % (sorted(tr), bool(c.get('backText'))))
print('  OK a second look starts clean')
PY
# a fix after the draft (re-cut, retime) then a change of look: the new look takes over, the reel's words stay
cp src/methodology/reels/sample-soft-story.config.ts "$ENG/qa/sample-soft-story-before.ts"
python3 scripts/retime_reel.py sample-soft-story --from "$ENG/qa/sample-soft-story-before.ts" >/dev/null
python3 scripts/make_style.py sample-soft-story clean-talk --in-place --force >/dev/null
python3 - <<'PY'
import sys
sys.path.insert(0, 'scripts')
import reel_config
c = reel_config.load('sample-soft-story')
tr = {e['style'] for e in c.get('effects', []) if e['kind'] == 'transition'}
ok = c['meta'].get('look') == 'clean-talk' and tr == {'flash'} and c.get('backText') and any(e['kind'] == 'card' for e in c['effects'])
if not ok:
    sys.exit('error: a restyle after a retime went wrong (look %s, transitions %s)' % (c['meta'].get('look'), sorted(tr)))
print('  OK a change of look after a fix')
PY
rm -f "$ENG/qa/sample-soft-story-before.ts"

say "4/4  The tools: a draft, a saved style, the Picker, a carousel, joined clips, beat versions"
T="$(mktemp -d)"
for f in picks default last; do [ -f "styles/$f.json" ] && cp "styles/$f.json" "$T/keep-$f.json"; done   # a re-run keeps their own picks and default
restore(){   # on success or failure: their own picks, default and last-time record come back, the test's are gone
  for f in picks default last; do
    if [ -f "$T/keep-$f.json" ]; then cp "$T/keep-$f.json" "styles/$f.json"; elif [ "$f" != last ]; then rm -f "styles/$f.json"; fi
  done
  rm -rf "$T"
}
trap restore EXIT
fail(){ echo "error: $*"; exit 1; }
scripts/make_reel.sh "$RAW" sample --draft >/dev/null && [ -s out/drafts/sample-DRAFT.mp4 ] || fail "the draft was not made"
echo "  OK draft"
python3 - <<'PAGES'
import json
p = open('qa/sample/storyboard/pane.html').read()
if 'data-comment' not in p or '<textarea' in p or len(json.load(open('qa/sample/storyboard/files-map.json'))) < 3:
    raise SystemExit('error: the storyboard page for beside the chat is wrong')
PAGES
python3 scripts/style_board.py >/dev/null && grep -q 'look-clean-talk' qa/style-board/pane.html || fail "the style board was not made"
python3 scripts/picker.py --pane >/dev/null && [ "$(python3 -c "import json; print(len(json.load(open('qa/picker/files-map.json'))))")" -gt 40 ] || fail "the Picker page was not made"
echo "  OK the pages beside the chat (storyboard, style board, Picker)"
[ -f styles/start-last.json ] && cp styles/start-last.json "$T/keep-start-last.json"
python3 scripts/start_page.py build --video "$RAW" --script samples/sample.txt >/dev/null && grep -q 'id="avs-start"' qa/start/pane.html || fail "the start page was not made"
python3 scripts/start_page.py read '{"captionStyle":"pill","effects":["counter","keycaps"],"placement":"organic","music":"none","script":""}' | grep -q '^START SAVED captions=pill' || fail "the start page picks did not save"
if [ -f "$T/keep-start-last.json" ]; then cp "$T/keep-start-last.json" styles/start-last.json; else rm -f styles/start-last.json; fi   # their own last picks stay
echo "  OK the start page"
python3 - <<'COLOR'
import os, subprocess, sys
sys.path.insert(0, 'scripts')
import reel_config, styles_lib
p = reel_config.config_path('sample-big-energy')
keep = open(p).read()
try:
    open(p, 'w').write(styles_lib.set_key(keep, 'color', 'cinematic', 'install test'))
    subprocess.run([sys.executable, 'scripts/color_lut.py', 'sample-big-energy'], check=True, capture_output=True)
    graded = reel_config.host_file(reel_config.load('sample-big-energy'))
    if not graded.endswith('-cut-c.mp4') or not os.path.exists(os.path.join('public', graded)):
        raise SystemExit('error: the color look did not grade the footage')
finally:
    open(p, 'w').write(keep)
    subprocess.run([sys.executable, 'scripts/color_lut.py', 'sample-big-energy'], check=False, capture_output=True)   # natural again: the graded copy goes
COLOR
echo "  OK a color look"
rm -rf styles/install-check styles/install-check-mix carousels/install-check   # leftovers from a run that failed partway
python3 scripts/my_styles.py new "Install Check" --like soft-story >/dev/null
python3 - <<'PY'
import json
p = 'styles/install-check/style.json'
st = json.load(open(p))
st.update({'captionStyle': 'bigword', 'look': {'captions': {'font': 'anton', 'color': '#FFFFFF'}}, 'transitions': {'first_join': 'flash'}})
json.dump(st, open(p, 'w'), indent=1)
PY
python3 scripts/make_style.py sample "install check" --force >/dev/null
node scripts/validate_reel.mjs sample-install-check >/dev/null || fail "a reel in a saved style did not validate"
echo "  OK saved style"
python3 scripts/picker.py --no-open --until-saved --port 8799 > "$T/picker.log" 2>&1 &
for i in 1 2 3 4 5 6 7 8 9 10; do grep -q "PICKER READY" "$T/picker.log" && break; sleep 1; done
P="$(sed -n 's/PICKER READY //p' "$T/picker.log")"
[ -n "$P" ] || fail "the Picker did not start"
curl -s "${P}api/state" | grep -q '"captions"' || fail "the Picker has no catalog"
curl -s -X POST -H 'Content-Type: application/json' -d '{"mode":"mix","captionStyle":"pill","effects":["keycaps"],"transitions":["flash"]}' "${P}api/picks" | grep -q '"ok"' || fail "the Picker did not save"
for i in 1 2 3 4 5; do grep -q "PICKS SAVED" "$T/picker.log" && break; sleep 1; done
python3 scripts/my_styles.py save "Install Check Mix" --from-picks >/dev/null || fail "the picks did not become a style"
echo "  OK Picker"
python3 scripts/carousel.py new "Install check" --from-reel sample >/dev/null
python3 - <<'PY'
import json
p = 'carousels/install-check/carousel.json'
d = json.load(open(p))
d['slides'] = [{'layout': 'hook', 'headline': 'An install ==check=='}, {'layout': 'statement', 'headline': 'Slides from ==your words=='},
               {'layout': 'cta', 'headline': 'All ==set==', 'keyword': 'OK'}]
d['approved'] = True
json.dump(d, open(p, 'w'), indent=1)
PY
python3 scripts/carousel.py render install-check --no-open >/dev/null || fail "the carousel did not render"
[ "$(ls carousels/install-check/slides/*.png | wc -l | tr -d ' ')" = 3 ] || fail "the carousel has the wrong number of slides"
echo "  OK carousel"
ffmpeg -v error -y -ss 0 -t 10 -i "$RAW" -c copy -metadata creation_time=2026-01-01T10:00:00Z "$T/a.mp4"
ffmpeg -v error -y -ss 10 -t 10 -i "$RAW" -c copy -metadata creation_time=2026-01-01T10:01:00Z "$T/b.mp4"
python3 scripts/join_clips.py "$T/a.mp4" "$T/b.mp4" --out "$T/joined.mp4" >/dev/null || fail "the clips did not join"
[ -s "$T/joined.mp4" ] || fail "no joined file"
echo "  OK joined clips"
python3 - "$T/opts.json" <<'PY'
import json, sys
sys.path.insert(0, 'scripts')
import reel_config, storyboard
cfg = reel_config.load('sample-big-energy')
b1 = storyboard.beats(cfg)[0]
w = next(w for w in cfg['words'] if w['t'] and w['t'].strip('.,').lower() == 'conversation')
f = round(w['s'] * 30)
a, b = max(b1['from'], f - 4), min(b1['to'], f + 40)
json.dump([{'label': 'Stamp', 'effects': [{'kind': 'word-stamp', 'in': a, 'out': b, 'word': 'conversation'}]},
           {'label': 'Nothing', 'effects': []}], open(sys.argv[1], 'w'))
PY
python3 scripts/beat_options.py sample-big-energy b01 --options "$T/opts.json" >/dev/null || fail "the beat versions did not render"
[ -s out/drafts/sample-big-energy-b01-a.mp4 ] && [ -s out/drafts/sample-big-energy-b01-b.mp4 ] || fail "a beat version is missing"
echo "  OK beat versions"
# clean up everything this step made
python3 - <<'PY'
import os, re, shutil
import glob
for d in ['styles/install-check', 'styles/install-check-mix', 'carousels/install-check', 'qa/sample-big-energy/options-b01.json',
          'src/methodology/reels/sample-soft-story.config.ts'] + glob.glob('out/drafts/sample*'):
    if os.path.isdir(d):
        shutil.rmtree(d)
    elif os.path.exists(d):
        os.remove(d)   # only the test's own drafts: theirs stay
for f in ('styles/picks.json', 'styles/default.json', 'src/methodology/reels/sample-install-check.config.ts'):
    if os.path.exists(f):
        os.remove(f)
p = 'src/methodology/Root.tsx'
s = open(p).read()
open(p, 'w').write(re.sub(r'    <Reel id="sample-(install-check|soft-story)" load=\{[^\n]*\n', '', s))
PY

mins=$(( ($(date +%s) - start + 59) / 60 ))
touch "$RE/runtime/.installed"   # the mark that setup finished (the skill and CLAUDE.md read it)
printf '\n\033[1;32mInstall test passed in about %d min.\033[0m The test video (Clean Talk) is %s/out/sample.mp4\n' "$mins" "$ENG"
echo "Open the folder: open \"$ENG/out\""
