#!/bin/bash
# AdCamp Video System install test: builds the included sample clip in the Clean Talk starter look and renders it,
# previews it in a second look (Big Energy), then checks the tools (draft, saved styles, the Picker, carousels,
# joined clips, beat versions, three covers, Lights Down, the pages beside the chat). Takes 10 to 15 minutes (longer on Intel). Safe to run again.
#   ~/AVS/tools/smoke_test.sh
# The sample is a real reel its owner already approved, so this test approves its own previews.
# Your own reels always wait for YOUR approval.
case "${1:-}" in -h|--help) sed -n '2,/^[^#]/p' "$0" | sed -n 's/^# \{0,1\}//p'; exit 0;; esac   # --help: the usage, nothing else
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
# the validator's planted faults (test_layout.mjs --self-test): on this cards-and-panels build here, on a full-screen look in
# step 3; every rule must find a place on one of the two. A member's own build runs only its reel's real checks.
node scripts/test_layout.mjs sample --self-test > qa/sample/self-test-panels.log || { cat qa/sample/self-test-panels.log; echo "error: the validator missed a planted fault"; exit 1; }
python3 scripts/make_style.py sample clean-talk --in-place --force
python3 samples/fill_sample.py
python3 scripts/verify_seams.py sample
scripts/make_reel.sh "$RAW" sample --outdoor --preview
ready sample

say "2/4  Render it, with the third cover picked (cover C)"
python3 - qa/sample/covers-given.json <<'PY'
import json, sys
sys.path.insert(0, 'scripts')
import reel_config
cfg = reel_config.load('sample')
w = [x for x in cfg['words'] if x['t']]
at = lambda t: next(round(x['s'] * 30) for x in w if x['t'].strip('.,').lower() == t)
json.dump({'b': {'frame': at('pays'), 'title': 'Four different chiropractors', 'accent': 'Four'},
           'c': {'frame': 45, 'title': 'Same four things', 'accent': 'four', 'back': 'four things', 'short': 'four',
                 'fallback': {'frame': at('conversations'), 'title': 'Four conversations', 'accent': 'Four'}}}, open(sys.argv[1], 'w'))
PY
python3 scripts/cover_options.py sample --options qa/sample/covers-given.json >/dev/null
python3 scripts/cover_options.py sample --pick c >/dev/null
python3 scripts/approve_reel.py sample --by "install test (sample clip)"
rm -f out/sample.mp4 out/sample-v*.mp4   # the test's own video: a re-run replaces it instead of adding a version
scripts/make_reel.sh "$RAW" sample --render   # any file the render could not load stops it (make_reel.sh reads its log)
python3 - out/sample.mp4 qa/sample/storyboard/covers/cover-c.png <<'PY'
import subprocess, sys
g = lambda f: subprocess.run(['ffmpeg', '-v', 'error', '-i', f, '-frames:v', '1', '-vf', 'scale=108:192,format=gray', '-f', 'rawvideo', '-'],
                             capture_output=True).stdout
a, b = g(sys.argv[1]), g(sys.argv[2])
d = sum(abs(x - y) for x, y in zip(a, b)) / float(max(len(a), 1))
if len(a) != len(b) or d > 6:
    sys.exit('error: frame 0 of the render is not cover C (it differs by %.1f): a file it draws did not load' % d)
PY
echo "  OK the render's first frame is the picked cover C, as its still shows it"

say "3/4  A second look from the same take: Big Energy (preview only)"
python3 scripts/make_style.py sample big-energy --force
"$AVS_MATTE_PYTHON" scripts/matte_reel.py sample-big-energy
python3 scripts/scene_map.py sample-big-energy
node scripts/test_layout.mjs sample-big-energy --self-test > qa/sample/self-test-full.log || { cat qa/sample/self-test-full.log; echo "error: the validator missed a planted fault"; exit 1; }
python3 - qa/sample/self-test-panels.log qa/sample/self-test-full.log <<'PY'
import re, sys
sk = [set(x.strip() for x in (re.search(r'\(skipped\): (.*)', open(f).read()) or [None, ''])[1].split(';') if x.strip()) for f in sys.argv[1:]]
both = sk[0] & sk[1]
if both:
    sys.exit('error: planted faults with no place on either test reel, so their rules went untested: %s' % ', '.join(sorted(both)))
PY
echo "  OK every planted fault caught by its own rule (cards and panels, then full screen)"
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

say "4/4  The tools: a draft, a saved style, the Picker, a carousel, joined clips, beat versions, covers, Lights Down"
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
python3 scripts/test_cutter.py > "$T/cutter.log" 2>&1 || { cat "$T/cutter.log"; fail "the cutter checks failed"; }
echo "  OK cutter checks (several trims, breaths inside pauses, transitions apart)"
python3 scripts/test_effect_kinds.py sample > "$T/kinds.log" 2>&1 || { cat "$T/kinds.log"; fail "a check could not read every effect kind"; }
echo "  OK every effect kind, retired ones too, reads in the checks"
node scripts/test_motion.mjs sample-big-energy > "$T/motion.log" 2>&1 || { cat "$T/motion.log"; fail "the zoom into screenshots or the drift on held graphics broke a rule"; }
echo "  OK the zoom into screenshots and the drift on held graphics"
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
json.dump([{'label': 'Snap', 'effects': [{'kind': 'snap-zoom', 'in': a, 'out': b, 'at': f + 2, 'scale': 1.15}]},
           {'label': 'Nothing', 'effects': []}], open(sys.argv[1], 'w'))
PY
python3 scripts/beat_options.py sample-big-energy b01 --options "$T/opts.json" >/dev/null || fail "the beat versions did not render"
[ -s out/drafts/sample-big-energy-b01-a.mp4 ] && [ -s out/drafts/sample-big-energy-b01-b.mp4 ] || fail "a beat version is missing"
echo "  OK beat versions"
# three covers on the storyboard: made from the sample's own words, a pick changes frame 0, a paid reel gets no words behind
cp src/methodology/reels/sample.config.ts "$T/sample-config.ts"; cp qa/sample/preview/f0000.png "$T/f0000.png"
python3 - "$T/covers.json" <<'PY'
import json, sys
sys.path.insert(0, 'scripts')
import reel_config
cfg = reel_config.load('sample')
w = [x for x in cfg['words'] if x['t']]
at = lambda t: next(round(x['s'] * 30) for x in w if x['t'].strip('.,').lower() == t)
json.dump({'b': {'frame': at('pays'), 'title': 'Four different chiropractors', 'accent': 'Four'},
           'c': {'frame': 45, 'title': 'Same four things', 'accent': 'four', 'back': 'four things', 'short': 'four',
                 'fallback': {'frame': at('conversations'), 'title': 'Four conversations', 'accent': 'Four'}}}, open(sys.argv[1], 'w'))
PY
python3 scripts/cover_options.py sample --options "$T/covers.json" > "$T/covers.log" 2>&1 || { cat "$T/covers.log"; fail "the three covers were not made"; }
for x in a b c; do [ -s "qa/sample/storyboard/covers/cover-$x.png" ] || fail "cover $x is missing"; done
grep -q 'id="cover-b"' qa/sample/storyboard/pane.html || fail "the storyboard has no cover row"
python3 scripts/cover_options.py sample --pick b >/dev/null || fail "the cover pick did not go in"
cmp -s "$T/f0000.png" qa/sample/preview/f0000.png && fail "picking cover B did not change the first frame"
python3 - "$T/covers.json" "$T/covers-paid.json" <<'PY'
import json, re, sys
t = open('src/methodology/reels/sample.config.ts').read().replace('"id": "sample"', '"id": "sample-paid-check"', 1)
t = t.replace('"placement": "organic"', '"placement": "paid"', 1)
t = re.sub(r'"post": \{[^}]*\}', '"post": {"keyword": "", "gets": "", "link": ""}', t, count=1)   # an ad has ad copy, no comment keyword
open('src/methodology/reels/sample-paid-check.config.ts', 'w').write(t)
g = json.load(open(sys.argv[1]))   # the same covers file as the regular post, plus the cover it had first
json.dump(dict(g, a={'frame': 45, 'title': 'Same four things', 'accent': 'four'}), open(sys.argv[2], 'w'))
PY
python3 scripts/cover_options.py sample-paid-check --options "$T/covers-paid.json" > "$T/covers-paid.log" 2>&1 || { cat "$T/covers-paid.log"; fail "the same covers file did not work on a paid ad"; }
python3 -c "import json,sys; d=json.load(open('qa/sample-paid-check/covers.json')); sys.exit(any(d['options'][x].get('back') for x in 'abc'))" \
  || fail "a paid ad was given words behind the head on its cover"
rm -f src/methodology/reels/sample-paid-check.config.ts; rm -rf qa/sample-paid-check qa/sample/covers.json qa/sample/storyboard/covers
cp "$T/sample-config.ts" src/methodology/reels/sample.config.ts; cp "$T/f0000.png" qa/sample/preview/f0000.png
python3 scripts/storyboard.py sample >/dev/null
echo "  OK covers (three to pick from, a pick changes the first frame, a paid ad gets its frame and title C)"
# Lights Down on one spoken line: its checks pass, its cutout is made and the part renders
python3 - "$T/lights.json" "$T/lights-beat" <<'PY'
import json, sys
sys.path.insert(0, 'scripts')
import reel_config, storyboard
cfg = reel_config.load('sample')
w = [x for x in cfg['words'] if x['t']]
a = round(next(x for x in w if x['t'].lower().startswith("they'd"))['s'] * 30) - 2
b = round(next(x for x in w if x['t'].strip('.').lower() == 'scratch')['e'] * 30) + 4
bt = next(x for x in storyboard.beats(cfg) if x['from'] <= a < x['to'])
b = min(b, bt['to'])
if b - a < 30:
    sys.exit('error: no line long enough for Lights Down in the sample')
json.dump([{'label': 'Lights down', 'effects': [{'kind': 'lights-down', 'in': a, 'out': b}]}, {'label': 'Nothing', 'effects': []}], open(sys.argv[1], 'w'))
open(sys.argv[2], 'w').write(bt['id'])
PY
LB="$(cat "$T/lights-beat")"
python3 scripts/beat_options.py sample "$LB" --options "$T/lights.json" > "$T/lights.log" 2>&1 || { cat "$T/lights.log"; fail "Lights Down did not pass its checks or render"; }
[ -s "out/drafts/sample-$LB-a.mp4" ] || fail "the Lights Down part was not rendered"
ls public/host/sample-fg-ld-*.webm >/dev/null 2>&1 || fail "the Lights Down cutout was not made"
rm -f "qa/sample/options-$LB.json" public/host/sample-fg-ld-*
echo "  OK Lights Down"
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
