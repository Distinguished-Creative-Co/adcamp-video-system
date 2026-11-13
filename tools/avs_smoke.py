"""avs smoke: the AVS install test (smoke_test.sh in Python, for a Mac and a Windows PC). Builds the included sample
clip in the Clean Talk starter look and renders it, previews it in a second look (Big Energy), then checks the tools
(draft, saved styles, the Picker, carousels, joined clips, beat versions, three covers, Lights Down, the pages beside the
chat). Takes 10 to 15 minutes on a Mac, longer on a PC. Safe to run again.
The sample is a real reel its owner already approved, so this test approves its own previews. Your own reels always
wait for YOUR approval.
"""
import codecs
import datetime
import filecmp
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import avs as A  # noqa: E402
import avs_platform as P  # noqa: E402
import avs_reel as R  # noqa: E402

ENG, PY, MPY, NODE = A.ENG, sys.executable, R.MPY, R.NODE
RAW = 'samples/sample.mp4'


class Failed(Exception):
    pass


def say(s):
    print('\n== %s' % s, flush=True)


def ok(s):
    print('  OK %s' % s, flush=True)


def fail(s):
    raise Failed('error: ' + s)


def run(cmd, log=None, quiet=False):
    """In the engine folder with the AVS environment. log: output into that file. quiet: output thrown away."""
    kw = {}
    if log:
        kw['stdout'] = open(log, 'w', encoding='utf-8', errors='replace')
        kw['stderr'] = subprocess.STDOUT
    elif quiet:
        kw['stdout'] = subprocess.DEVNULL
    try:
        return subprocess.run(cmd, cwd=ENG, env=A.env(), **kw).returncode
    finally:
        if log:
            kw['stdout'].close()


def py(script, *a, **kw):
    return run([PY, script if '/' in script else os.path.join('scripts', script)] + list(a), **kw)


def must(rc, what):
    if rc:
        raise Failed(what or '')


def node(script, *a, **kw):
    return run([NODE, os.path.join('scripts', script)] + list(a), **kw)


def code(src, *a, **kw):
    return run([PY, '-c', src] + list(a), **kw)


def reel(*a):
    must(R.main(list(a)), 'error: the reel step failed: avs reel %s' % ' '.join(a))


def ready(name):
    p = os.path.join(ENG, 'script', name + '-scene-map.md')
    if not (os.path.exists(p) and re.search(r'^\*\*Status: READY', open(p, encoding='utf-8').read(), re.M)):
        fail('the %s preview is not ready, see script/%s-scene-map.md' % (name, name))


def cat(p):
    if os.path.exists(p):
        print(open(p, encoding='utf-8', errors='replace').read())


def rm(*paths):
    for p in paths:
        for f in glob.glob(os.path.join(ENG, p)):
            if os.path.isdir(f):
                shutil.rmtree(f, ignore_errors=True)
            else:
                os.remove(f)


E = os.path.join   # short for the checks below
COVERS_GIVEN = r'''
import json, sys
sys.path.insert(0, 'scripts')
import reel_config
cfg = reel_config.load('sample')
w = [x for x in cfg['words'] if x['t']]
at = lambda t: next(round(x['s'] * 30) for x in w if x['t'].strip('.,').lower() == t)
json.dump({'b': {'frame': at('pays'), 'title': 'Four different chiropractors', 'accent': 'Four'},
           'c': {'frame': 45, 'title': 'Same four things', 'accent': 'four', 'back': 'four things', 'short': 'four',
                 'fallback': {'frame': at('conversations'), 'title': 'Four conversations', 'accent': 'Four'}}}, open(sys.argv[1], 'w'))
'''
FRAME0 = r'''
import subprocess, sys
g = lambda f: subprocess.run(['ffmpeg', '-v', 'error', '-i', f, '-frames:v', '1', '-vf', 'scale=108:192,format=gray', '-f', 'rawvideo', '-'],
                             capture_output=True).stdout
a, b = g(sys.argv[1]), g(sys.argv[2])
d = sum(abs(x - y) for x, y in zip(a, b)) / float(max(len(a), 1))
if len(a) != len(b) or d > 6:
    sys.exit('error: frame 0 of the render is not cover C (it differs by %.1f): a file it draws did not load' % d)
'''
SKIPPED = r'''
import re, sys
sk = [set(x.strip() for x in (re.search(r'\(skipped\): (.*)', open(f).read()) or [None, ''])[1].split(';') if x.strip()) for f in sys.argv[1:]]
both = sk[0] & sk[1]
if both:
    sys.exit('error: planted faults with no place on either test reel, so their rules went untested: %s' % ', '.join(sorted(both)))
'''
SOFT = r'''
import sys
sys.path.insert(0, 'scripts')
import reel_config
c = reel_config.load('sample-soft-story')
tr = {e['style'] for e in c.get('effects', []) if e['kind'] == 'transition'}
if c.get('backText') or not tr or tr - {'iris'}:
    sys.exit('error: the Soft Story version kept the Clean Talk look (transitions %s, hook title %s)' % (sorted(tr), bool(c.get('backText'))))
print('  OK a second look starts clean')
'''
RESTYLE = r'''
import sys
sys.path.insert(0, 'scripts')
import reel_config
c = reel_config.load('sample-soft-story')
tr = {e['style'] for e in c.get('effects', []) if e['kind'] == 'transition'}
ok = c['meta'].get('look') == 'clean-talk' and tr == {'flash'} and c.get('backText') and any(e['kind'] == 'card' for e in c['effects'])
if not ok:
    sys.exit('error: a restyle after a retime went wrong (look %s, transitions %s)' % (c['meta'].get('look'), sorted(tr)))
print('  OK a change of look after a fix')
'''
PAGES = r'''
import json
p = open('qa/sample/storyboard/pane.html', encoding='utf-8').read()
if 'data-comment' not in p or '<textarea' in p or len(json.load(open('qa/sample/storyboard/files-map.json'))) < 3:
    raise SystemExit('error: the storyboard page for beside the chat is wrong')
'''
COLOR = r'''
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
    subprocess.run([sys.executable, 'scripts/color_lut.py', 'sample-big-energy'], check=False, capture_output=True)
'''
STYLE_EDIT = r'''
import json
p = 'styles/install-check/style.json'
st = json.load(open(p))
st.update({'captionStyle': 'bigword', 'look': {'captions': {'font': 'anton', 'color': '#FFFFFF'}}, 'transitions': {'first_join': 'flash'}})
json.dump(st, open(p, 'w'), indent=1)
'''
CAROUSEL = r'''
import json
p = 'carousels/install-check/carousel.json'
d = json.load(open(p))
d['slides'] = [{'layout': 'hook', 'headline': 'An install ==check=='}, {'layout': 'statement', 'headline': 'Slides from ==your words=='},
               {'layout': 'cta', 'headline': 'All ==set==', 'keyword': 'OK'}]
d['approved'] = True
json.dump(d, open(p, 'w'), indent=1)
'''
BEATS = r'''
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
'''
PAID = r'''
import json, re, sys
t = open('src/methodology/reels/sample.config.ts').read().replace('"id": "sample"', '"id": "sample-paid-check"', 1)
t = t.replace('"placement": "organic"', '"placement": "paid"', 1)
t = re.sub(r'"post": \{[^}]*\}', '"post": {"keyword": "", "gets": "", "link": ""}', t, count=1)
open('src/methodology/reels/sample-paid-check.config.ts', 'w').write(t)
g = json.load(open(sys.argv[1]))
json.dump(dict(g, a={'frame': 45, 'title': 'Same four things', 'accent': 'four'}), open(sys.argv[2], 'w'))
'''
LIGHTS = r'''
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
'''
CLEANUP = r'''
import os, re, shutil, glob
for d in ['styles/install-check', 'styles/install-check-mix', 'carousels/install-check', 'qa/sample-big-energy/options-b01.json',
          'src/methodology/reels/sample-soft-story.config.ts'] + glob.glob('out/drafts/sample*'):
    if os.path.isdir(d):
        shutil.rmtree(d)
    elif os.path.exists(d):
        os.remove(d)
for f in ('styles/picks.json', 'styles/default.json', 'src/methodology/reels/sample-install-check.config.ts'):
    if os.path.exists(f):
        os.remove(f)
p = 'src/methodology/Root.tsx'
s = open(p).read()
open(p, 'w').write(re.sub(r'    <Reel id="sample-(install-check|soft-story)" load=\{[^\n]*\n', '', s))
'''


def part1():
    say('1/4  Your test video: cut the sample (keeps the last clean take of each line), in the Clean Talk look')
    os.makedirs(E(ENG, 'script', 'word-timings'), exist_ok=True)
    shutil.copy2(E(ENG, 'samples', 'sample.txt'), E(ENG, 'script', 'sample.txt'))
    shutil.copy2(E(ENG, 'samples', 'sample-trims.json'), E(ENG, 'script', 'word-timings', 'sample-trims.json'))
    reel(RAW, 'sample', '--face', '510,760', '--outdoor', '--regen', '--preview')   # --regen: always a fresh config
    print('(Expected on this first pass: NOT READY, the copy is blank and a few breaths between takes are flagged. The next steps set the look, fill the copy and sign off those breaths.)')
    os.makedirs(E(ENG, 'qa', 'sample'), exist_ok=True)
    if node('test_layout.mjs', 'sample', '--self-test', log=E(ENG, 'qa', 'sample', 'self-test-panels.log')):
        cat(E(ENG, 'qa', 'sample', 'self-test-panels.log'))
        fail('the validator missed a planted fault')
    must(py('make_style.py', 'sample', 'clean-talk', '--in-place', '--force'), 'error: make_style failed')
    must(py('samples/fill_sample.py'), 'error: fill_sample failed')
    must(py('verify_seams.py', 'sample'), 'error: the seam check failed')
    reel(RAW, 'sample', '--outdoor', '--preview')
    ready('sample')


def part2():
    say('2/4  Render it, with the third cover picked (cover C)')
    must(code(COVERS_GIVEN, 'qa/sample/covers-given.json'), 'error: the covers file was not made')
    must(py('cover_options.py', 'sample', '--options', 'qa/sample/covers-given.json', quiet=True), 'error: the covers were not made')
    must(py('cover_options.py', 'sample', '--pick', 'c', quiet=True), 'error: cover C was not picked')
    must(py('approve_reel.py', 'sample', '--by', 'install test (sample clip)'), 'error: the approval was refused')
    rm('out/sample.mp4', 'out/sample-v*.mp4')   # the test's own video: a re-run replaces it
    reel(RAW, 'sample', '--render')
    must(code(FRAME0, 'out/sample.mp4', 'qa/sample/storyboard/covers/cover-c.png'), '')
    ok("the render's first frame is the picked cover C, as its still shows it")


def part3():
    say('3/4  A second look from the same take: Big Energy (preview only)')
    must(py('make_style.py', 'sample', 'big-energy', '--force'), 'error: make_style failed')
    must(run([MPY, 'scripts/matte_reel.py', 'sample-big-energy']), 'error: the cutout failed')
    must(py('scene_map.py', 'sample-big-energy'), 'error: the scene map failed')
    if node('test_layout.mjs', 'sample-big-energy', '--self-test', log=E(ENG, 'qa', 'sample', 'self-test-full.log')):
        cat(E(ENG, 'qa', 'sample', 'self-test-full.log'))
        fail('the validator missed a planted fault')
    must(code(SKIPPED, 'qa/sample/self-test-panels.log', 'qa/sample/self-test-full.log'), '')
    ok('every planted fault caught by its own rule (cards and panels, then full screen)')
    ready('sample-big-energy')
    py('extract_reel_stills.py', 'sample-big-energy', '--preview', quiet=True)
    py('make_style.py', 'sample', 'soft-story', '--force', quiet=True)
    must(code(SOFT), '')
    shutil.copy2(E(ENG, 'src', 'methodology', 'reels', 'sample-soft-story.config.ts'), E(ENG, 'qa', 'sample-soft-story-before.ts'))
    py('retime_reel.py', 'sample-soft-story', '--from', E(ENG, 'qa', 'sample-soft-story-before.ts'), quiet=True)
    py('make_style.py', 'sample-soft-story', 'clean-talk', '--in-place', '--force', quiet=True)
    must(code(RESTYLE), '')
    rm('qa/sample-soft-story-before.ts')


def picker_check(T):
    log = E(T, 'picker.log')
    lf = open(log, 'w', encoding='utf-8')
    p = subprocess.Popen([PY, 'scripts/picker.py', '--no-open', '--until-saved', '--port', '8799'], cwd=ENG, env=A.env(), stdout=lf, stderr=subprocess.STDOUT)
    try:
        url = ''
        for _ in range(15):
            m = re.search(r'PICKER READY (\S+)', open(log, encoding='utf-8', errors='replace').read())
            if m:
                url = m.group(1)
                break
            time.sleep(1)
        if not url:
            fail('the Picker did not start')
        if '"captions"' not in urllib.request.urlopen(url + 'api/state', timeout=20).read().decode('utf-8'):
            fail('the Picker has no catalog')
        body = json.dumps({'mode': 'mix', 'captionStyle': 'pill', 'effects': ['keycaps'], 'transitions': ['flash']}).encode()
        req = urllib.request.Request(url + 'api/picks', data=body, headers={'Content-Type': 'application/json'}, method='POST')
        if '"ok"' not in urllib.request.urlopen(req, timeout=20).read().decode('utf-8'):
            fail('the Picker did not save')
        for _ in range(5):
            if 'PICKS SAVED' in open(log, encoding='utf-8', errors='replace').read():
                break
            time.sleep(1)
    finally:
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()
        lf.close()
    must(py('my_styles.py', 'save', 'Install Check Mix', '--from-picks', quiet=True), 'error: the picks did not become a style')
    ok('Picker')


def part4(T):
    say('4/4  The tools: a draft, a saved style, the Picker, a carousel, joined clips, beat versions, covers, Lights Down')
    reel(RAW, 'sample', '--draft')
    p = E(ENG, 'out', 'drafts', 'sample-DRAFT.mp4')
    if not (os.path.exists(p) and os.path.getsize(p)):
        fail('the draft was not made')
    ok('draft')
    if py('test_cutter.py', log=E(T, 'cutter.log')):
        cat(E(T, 'cutter.log')); fail('the cutter checks failed')
    ok('cutter checks (several trims, breaths inside pauses, transitions apart)')
    if py('test_effect_kinds.py', 'sample', log=E(T, 'kinds.log')):
        cat(E(T, 'kinds.log')); fail('a check could not read every effect kind')
    ok('every effect kind, retired ones too, reads in the checks')
    if node('test_motion.mjs', 'sample-big-energy', log=E(T, 'motion.log')):
        cat(E(T, 'motion.log')); fail('the zoom into screenshots or the drift on held graphics broke a rule')
    ok('the zoom into screenshots and the drift on held graphics')
    must(code(PAGES), '')
    if py('style_board.py', quiet=True) or 'look-clean-talk' not in open(E(ENG, 'qa', 'style-board', 'pane.html'), encoding='utf-8').read():
        fail('the style board was not made')
    if py('picker.py', '--pane', quiet=True) or len(json.load(open(E(ENG, 'qa', 'picker', 'files-map.json')))) <= 40:
        fail('the Picker page was not made')
    ok('the pages beside the chat (storyboard, style board, Picker)')
    sl = E(ENG, 'styles', 'start-last.json')
    if os.path.exists(sl):
        shutil.copy2(sl, E(T, 'keep-start-last.json'))
    if py('start_page.py', 'build', '--video', RAW, '--script', 'samples/sample.txt', quiet=True) or \
            'id="avs-start"' not in open(E(ENG, 'qa', 'start', 'pane.html'), encoding='utf-8').read():
        fail('the start page was not made')
    r = subprocess.run([PY, 'scripts/start_page.py', 'read', json.dumps({'captionStyle': 'pill', 'effects': ['counter', 'keycaps'], 'placement': 'organic', 'music': 'none', 'script': ''})],
                       cwd=ENG, env=A.env(), capture_output=True, text=True, encoding='utf-8', errors='replace')
    if not re.search(r'^START SAVED captions=pill', r.stdout, re.M):
        fail('the start page picks did not save')
    if os.path.exists(E(T, 'keep-start-last.json')):
        shutil.copy2(E(T, 'keep-start-last.json'), sl)
    elif os.path.exists(sl):
        os.remove(sl)   # their own last picks stay
    ok('the start page')
    must(code(COLOR), '')
    ok('a color look')
    rm('styles/install-check', 'styles/install-check-mix', 'carousels/install-check')   # leftovers from a run that failed partway
    py('my_styles.py', 'new', 'Install Check', '--like', 'soft-story', quiet=True)
    must(code(STYLE_EDIT), '')
    py('make_style.py', 'sample', 'install check', '--force', quiet=True)
    if node('validate_reel.mjs', 'sample-install-check', quiet=True):
        fail('a reel in a saved style did not validate')
    ok('saved style')
    picker_check(T)
    py('carousel.py', 'new', 'Install check', '--from-reel', 'sample', quiet=True)
    must(code(CAROUSEL), '')
    if py('carousel.py', 'render', 'install-check', '--no-open', quiet=True):
        fail('the carousel did not render')
    if len(glob.glob(E(ENG, 'carousels', 'install-check', 'slides', '*.png'))) != 3:
        fail('the carousel has the wrong number of slides')
    ok('carousel')
    a_, b_, j = E(T, 'a.mp4'), E(T, 'b.mp4'), E(T, 'joined.mp4')
    run(['ffmpeg', '-v', 'error', '-y', '-ss', '0', '-t', '10', '-i', RAW, '-c', 'copy', '-metadata', 'creation_time=2026-01-01T10:00:00Z', a_])
    run(['ffmpeg', '-v', 'error', '-y', '-ss', '10', '-t', '10', '-i', RAW, '-c', 'copy', '-metadata', 'creation_time=2026-01-01T10:01:00Z', b_])
    if py('join_clips.py', a_, b_, '--out', j, quiet=True):
        fail('the clips did not join')
    if not (os.path.exists(j) and os.path.getsize(j)):
        fail('no joined file')
    ok('joined clips')
    must(code(BEATS, E(T, 'opts.json')), '')
    if py('beat_options.py', 'sample-big-energy', 'b01', '--options', E(T, 'opts.json'), quiet=True):
        fail('the beat versions did not render')
    for x in 'ab':
        f = E(ENG, 'out', 'drafts', 'sample-big-energy-b01-%s.mp4' % x)
        if not (os.path.exists(f) and os.path.getsize(f)):
            fail('a beat version is missing')
    ok('beat versions')
    # three covers on the storyboard: made from the sample's own words, a pick changes frame 0, a paid reel gets no words behind
    cfgp, f0 = E(ENG, 'src', 'methodology', 'reels', 'sample.config.ts'), E(ENG, 'qa', 'sample', 'preview', 'f0000.png')
    shutil.copy2(cfgp, E(T, 'sample-config.ts')); shutil.copy2(f0, E(T, 'f0000.png'))
    must(code(COVERS_GIVEN, E(T, 'covers.json')), '')
    if py('cover_options.py', 'sample', '--options', E(T, 'covers.json'), log=E(T, 'covers.log')):
        cat(E(T, 'covers.log')); fail('the three covers were not made')
    for x in 'abc':
        f = E(ENG, 'qa', 'sample', 'storyboard', 'covers', 'cover-%s.png' % x)
        if not (os.path.exists(f) and os.path.getsize(f)):
            fail('cover %s is missing' % x)
    if 'id="cover-b"' not in open(E(ENG, 'qa', 'sample', 'storyboard', 'pane.html'), encoding='utf-8').read():
        fail('the storyboard has no cover row')
    if py('cover_options.py', 'sample', '--pick', 'b', quiet=True):
        fail('the cover pick did not go in')
    if filecmp.cmp(E(T, 'f0000.png'), f0, shallow=False):
        fail('picking cover B did not change the first frame')
    must(code(PAID, E(T, 'covers.json'), E(T, 'covers-paid.json')), '')
    if py('cover_options.py', 'sample-paid-check', '--options', E(T, 'covers-paid.json'), log=E(T, 'covers-paid.log')):
        cat(E(T, 'covers-paid.log')); fail('the same covers file did not work on a paid ad')
    d = json.load(open(E(ENG, 'qa', 'sample-paid-check', 'covers.json')))
    if any(d['options'][x].get('back') for x in 'abc'):
        fail('a paid ad was given words behind the head on its cover')
    rm('src/methodology/reels/sample-paid-check.config.ts', 'qa/sample-paid-check', 'qa/sample/covers.json', 'qa/sample/storyboard/covers')
    shutil.copy2(E(T, 'sample-config.ts'), cfgp); shutil.copy2(E(T, 'f0000.png'), f0)
    py('storyboard.py', 'sample', quiet=True)
    ok('covers (three to pick from, a pick changes the first frame, a paid ad gets its frame and title C)')
    must(code(LIGHTS, E(T, 'lights.json'), E(T, 'lights-beat')), '')
    lb = open(E(T, 'lights-beat')).read().strip()
    if py('beat_options.py', 'sample', lb, '--options', E(T, 'lights.json'), log=E(T, 'lights.log')):
        cat(E(T, 'lights.log')); fail('Lights Down did not pass its checks or render')
    f = E(ENG, 'out', 'drafts', 'sample-%s-a.mp4' % lb)
    if not (os.path.exists(f) and os.path.getsize(f)):
        fail('the Lights Down part was not rendered')
    if not glob.glob(E(ENG, 'public', 'host', 'sample-fg-ld-*.webm')):
        fail('the Lights Down cutout was not made')
    rm('qa/sample/options-%s.json' % lb, 'public/host/sample-fg-ld-*')
    ok('Lights Down')
    must(code(CLEANUP), '')


PARTS = {'1/4': 'cutting the sample', '2/4': 'the render', '3/4': 'the second look', '4/4': 'the tool checks'}


def recorded(argv):
    """Runs the test in a child process: its output shows as it comes and is kept in runtime/logs/test-video.log, and the
    result goes in steps.log, where avs doctor and avs report read it. A run that never finishes leaves its start there."""
    os.makedirs(A.LOGS, exist_ok=True)
    log = os.path.join(A.LOGS, 'test-video.log')
    A.log_step('test-video', None, 0, 'started')
    t0 = time.time()
    e = dict(os.environ, AVS_SMOKE_CHILD='1', PYTHONUNBUFFERED='1')
    dec = codecs.getincrementaldecoder('utf-8')('replace')
    with open(log, 'w', encoding='utf-8', errors='replace') as f:
        f.write('AVS test video, %s, %s GB of memory\n' % (datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), '%.0f' % P.ram_gb()))
        p = subprocess.Popen([sys.executable, os.path.abspath(__file__)] + list(argv), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=e)
        while True:
            b = os.read(p.stdout.fileno(), 65536)
            if not b:
                break
            t = dec.decode(b)
            sys.stdout.write(t)
            sys.stdout.flush()
            f.write(t)
            f.flush()
        rc = p.wait()
    text = open(log, encoding='utf-8', errors='replace').read().replace('\r\n', '\n')
    lines = [x.rsplit('\r', 1)[-1].strip() for x in text.split('\n')]
    lines = [x for x in lines if x]
    if rc == 0:
        A.log_step('test-video', True, time.time() - t0, 'passed')
        return 0
    part = ([x[3:6] for x in lines if x.startswith('== ') and x[3:6] in PARTS] or [''])[-1]
    where = 'at %s (%s): ' % (part, PARTS[part]) if part else ''
    A.log_step('test-video', False, time.time() - t0, where + (lines[-1] if lines else 'no output, exit code %d' % rc))
    return rc


def main(argv):
    if argv and argv[0] in ('-h', '--help'):
        print(__doc__.strip())
        return 0
    if os.environ.get('AVS_SMOKE_CHILD') != '1':
        return recorded(argv)
    if not os.path.exists(P.venv_python(A.WHISPERX)):
        print('error: AVS is not installed. Run: avs install --all')
        return 1
    os.environ.update(A.env())
    os.chdir(ENG)   # as smoke_test.sh's `cd "$ENG"`: the sample's path below is the engine folder's
    start = time.time()
    T = tempfile.mkdtemp(prefix='avs-smoke-')
    keep = {}
    try:
        part1()
        part2()
        part3()
        for f in ('picks', 'default', 'last'):   # a re-run keeps their own picks and default
            p = E(ENG, 'styles', f + '.json')
            if os.path.exists(p):
                shutil.copy2(p, E(T, 'keep-%s.json' % f)); keep[f] = True
        try:
            part4(T)
        finally:   # on success or failure: their own picks, default and last-time record come back, the test's are gone
            for f in ('picks', 'default', 'last'):
                p = E(ENG, 'styles', f + '.json')
                if keep.get(f):
                    shutil.copy2(E(T, 'keep-%s.json' % f), p)
                elif f != 'last' and os.path.exists(p):
                    os.remove(p)
    except Failed as e:
        if str(e):
            print(str(e))
        return 1
    finally:
        shutil.rmtree(T, ignore_errors=True)
    open(E(A.RT, '.installed'), 'a').close()   # the mark that setup finished (the skill and CLAUDE.md read it)
    mins = int((time.time() - start + 59) // 60)
    print('\nInstall test passed in about %d min. The test video (Clean Talk) is %s' % (mins, E(ENG, 'out', 'sample.mp4')))
    print('Open the folder: avs open out')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
