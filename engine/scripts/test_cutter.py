#!/usr/bin/env python3
"""Regression checks for the cutter (last_take.py) and the transitions on its joins. Synthetic words and silences:
no footage, no ffmpeg, a few seconds.

    python3 scripts/test_cutter.py

1. Every --trim given in one run applies, and the trims file and the command line behave the same: a trim added to
   <name>-trims.json by hand applies on the next cut, a repeated trim is saved once, a trim through a word stops the
   cut and is never saved, and make_reel.sh re-cuts when the trims file changes.
2. A pause between sentences broken by breaths (silence, breath, silence, breath, silence) becomes one join, never
   picture pieces under 0.4s, and no two transitions sit within 13 frames of each other (where a look places them,
   and at the render gate).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import hostcut  # noqa: E402
import last_take  # noqa: E402
import styles_lib  # noqa: E402


def W(t, a, b):
    return {'word': t, 'start': a, 'end': b}


# three sentences in one kept group. The pause after "here." is three silences split by two breaths (60 and 40 ms),
# the way a phone records someone breathing between lines. "Second" has a mid-sentence pause (7.45-7.9) and the
# third sentence a doubled "line" (a fumble the aligner keeps), so both can be trimmed with edges in silence.
WORDS = [W('First', .5, .8), W('line', .8, 1.0), W('is', 1.0, 1.1), W('here.', 1.1, 1.5),
         W('Second', 7.05, 7.4), W('line', 7.95, 8.15), W('comes', 8.15, 8.45), W('next.', 8.45, 8.8),
         W('Third', 9.4, 9.7), W('line', 10.15, 10.4), W('line', 10.95, 11.2), W('ends', 11.2, 11.5), W('it.', 11.5, 11.8)]
SCRIPT = 'First line is here. Second line comes next.\n\nThird line ends it.\n'
SIL = [(0.0, .45), (1.55, 3.6), (3.66, 6.0), (6.04, 7.0), (7.45, 7.9), (8.85, 9.35), (9.75, 10.1), (10.45, 10.9), (11.85, 13.0)]
DUR = 13.0
TRIM_A, TRIM_B, TRIM_HAND, TRIM_BAD = (7.5, 7.85), (9.8, 10.85), (0.1, 0.44), (1.0, 1.3)
PIECE = 0.40   # the requirement: no picture piece shorter than this inside a pause

FAILS = []


def check(ok, what):
    print('  %s %s' % ('OK  ' if ok else 'FAIL', what))
    if not ok:
        FAILS.append(what)


def fake_render(a, rec, keep, S, dur, forbidden):
    hostcut.assert_cuts_in_silence(keep, S, dur, min_join_silence=last_take.MIN_JOIN, forbidden_spans=forbidden)
    rec['keep'] = [list(k) for k in keep]
    return keep


# the cutter without ffmpeg: room tone, duration and the silence map are the synthetic ones above
last_take.rms_floor = lambda src: -60.0
last_take.render = fake_render
hostcut.probe_duration = lambda src: DUR
hostcut.detect_silences = lambda *a, **k: list(SIL)


def cut(d, *extra):
    """One last_take run in folder d. Returns (record, error or None)."""
    sys.argv = ['last_take.py', os.path.join(d, 'src.mp4'), '--words', os.path.join(d, 'wx.json'), '--script', os.path.join(d, 'script.txt'),
                '--out', os.path.join(d, 'cut.mp4'), '--report', os.path.join(d, 'takes.md'), '--json', os.path.join(d, 't-takes.json')] + list(extra)
    err = None
    try:
        last_take.main()
    except SystemExit as ex:
        err = str(ex)
    except Exception as ex:  # noqa: BLE001  (a crash is a failed check, not a stopped test)
        err = '%s: %s' % (type(ex).__name__, ex)
    return json.load(open(os.path.join(d, 't-takes.json'))), err


def kept(rec, span):
    return any(s < span[1] and e > span[0] for s, e in rec['keep'])


def saved(d):
    p = os.path.join(d, 't-trims.json')
    return [tuple(t['raw']) for t in json.load(open(p))] if os.path.exists(p) else []


def test_trims_and_breaths():
    d = tempfile.mkdtemp(prefix='avs-test-cutter-')
    open(os.path.join(d, 'src.mp4'), 'w').close()
    json.dump(WORDS, open(os.path.join(d, 'wx.json'), 'w'))
    open(os.path.join(d, 'script.txt'), 'w').write(SCRIPT)
    import contextlib
    import io
    quiet = io.StringIO()

    print('1. trims')
    with contextlib.redirect_stdout(quiet):
        cut(d)   # the first cut, then two fumbles trimmed in one go
        rec, err = cut(d, '--trim', '%g-%g' % TRIM_A, '--trim', '%g-%g' % TRIM_B)
    check(err is None and rec['gate'] == 'PASS', 'two --trim in one run cut cleanly (%s)' % (err or rec['gate']))
    check(not kept(rec, TRIM_A) and not kept(rec, TRIM_B), 'both trims are out of the cut, not just the last one')
    check(saved(d) == [TRIM_A, TRIM_B], 'both trims saved to the trims file')

    tf = os.path.join(d, 't-trims.json')
    json.dump(json.load(open(tf)) + [{'raw': list(TRIM_HAND), 'why': 'added by hand'}], open(tf, 'w'), indent=1)
    with contextlib.redirect_stdout(quiet):
        rec, err = cut(d)
    check(err is None and not kept(rec, TRIM_HAND) and not kept(rec, TRIM_A), 'a trim added to the file by hand applies on the next cut, with no --trim')

    with contextlib.redirect_stdout(quiet):
        rec, err = cut(d, '--trim', '%g-%g' % TRIM_A)
    check(err is None and len(saved(d)) == 3, 'a trim given again is saved once')

    with contextlib.redirect_stdout(quiet):
        rec, err = cut(d, '--trim', '%g-%g' % TRIM_BAD)
    check(err is not None and any('not saved: --trim 1.00-1.30' in e for e in rec['errors']), 'a trim through a word stops the cut and says it was not saved')
    check(len(saved(d)) == 3, 'the trim through a word is not in the file')

    print('2. breaths inside a pause')
    with contextlib.redirect_stdout(quiet):
        rec, err = cut(d)
    mids = [(w['start'] + w['end']) / 2 for w in WORDS]
    tiny = [k for k in rec['keep'] if k[1] - k[0] < PIECE and not any(k[0] <= m <= k[1] for m in mids)]
    check(not tiny, 'no picture piece under %.1fs without a word (found %s)' % (PIECE, tiny))
    inside = [k for k in rec['keep'] if 1.7 < k[0] < 6.8 or 1.7 < k[1] < 6.8]
    check(not inside, 'the broken pause after "here." is one join (no segment starts or ends inside it)')
    check(len(rec.get('slivers', [])) == 2, 'the two breaths are listed as dropped in the takes record')
    whole = lambda w: any(s <= w['start'] and e >= w['end'] for s, e in rec['keep'])  # noqa: E731
    check(all(whole(w) for w in WORDS if w is not WORDS[9]), 'every word except the trimmed fumble is still in the cut, whole')
    short = [(0, 2), (2.5, 2.8), (3, 5)]
    check(getattr(last_take, 'drop_slivers', lambda k, w: ([],))(short, [W('Yes.', 2.55, 2.75)])[0] == short, 'a short piece that holds a word is kept')
    shutil.rmtree(d, ignore_errors=True)


def test_make_reel_recut():
    """make_reel.sh's step-2 condition, run as written: a trims file newer than the cut forces a fresh cut. On Windows,
    where there is no bash, the same condition in the launcher's video chain (tools/avs_reel.py, needs_cut)."""
    print('3. make_reel.sh re-cuts when the trims file changes')
    if sys.platform == 'win32':
        return _test_recut_launcher()
    src = open(os.path.join(HERE, 'make_reel.sh')).read()
    lines = [re.search(p, src, re.M) for p in (r'^newer\(\)\{.*$', r'^WX=.*$', r'^CUT=.*$', r'^TRIMS=.*$', r'^if \[ -n "\$TAKES" \].*; then$')]
    if not all(lines):
        check(False, 'make_reel.sh step-2 lines found')
        return
    cond = lines[-1].group(0)[:-len('then')] + 'then echo RECUT; else echo FRESH; fi'
    d = tempfile.mkdtemp(prefix='avs-test-recut-')
    for p in ('script/t.txt', 'script/word-timings/t-wx.json', 'public/host/t-cut.mp4'):
        os.makedirs(os.path.dirname(os.path.join(d, p)), exist_ok=True)
        open(os.path.join(d, p), 'w').close()
    t0 = 1700000000
    for p, t in (('script/t.txt', t0), ('script/word-timings/t-wx.json', t0), ('public/host/t-cut.mp4', t0 + 10)):
        os.utime(os.path.join(d, p), (t, t))
    sh = '\n'.join(['NAME=t', 'TAKES=""'] + [m.group(0) for m in lines[:-1]] + [cond])
    run = lambda: subprocess.run(['bash', '-c', sh], cwd=d, capture_output=True, text=True).stdout.strip()  # noqa: E731
    check(run() == 'FRESH', 'no trims file: the cut is reused')
    tf = os.path.join(d, 'script/word-timings/t-trims.json')
    open(tf, 'w').write('[]')
    os.utime(tf, (t0 + 20, t0 + 20))
    check(run() == 'RECUT', 'a trims file newer than the cut (edited by hand) re-cuts')
    os.utime(os.path.join(d, 'public/host/t-cut.mp4'), (t0 + 30, t0 + 30))
    check(run() == 'FRESH', 'after the re-cut the cut is reused again')
    shutil.rmtree(d, ignore_errors=True)


def _test_recut_launcher():
    sys.path.insert(0, os.path.join(os.path.dirname(ROOT), 'tools'))
    import avs_reel
    d = tempfile.mkdtemp(prefix='avs-test-recut-')
    for p in ('script/t.txt', 'script/word-timings/t-wx.json', 'public/host/t-cut.mp4'):
        os.makedirs(os.path.dirname(os.path.join(d, p)), exist_ok=True)
        open(os.path.join(d, p), 'w').close()
    t0 = 1700000000
    for p, t in (('script/t.txt', t0), ('script/word-timings/t-wx.json', t0), ('public/host/t-cut.mp4', t0 + 10)):
        os.utime(os.path.join(d, p), (t, t))
    run = lambda: 'RECUT' if avs_reel.needs_cut('t', root=d) else 'FRESH'  # noqa: E731
    check(run() == 'FRESH', 'no trims file: the cut is reused')
    tf = os.path.join(d, 'script/word-timings/t-trims.json')
    open(tf, 'w').write('[]')
    os.utime(tf, (t0 + 20, t0 + 20))
    check(run() == 'RECUT', 'a trims file newer than the cut (edited by hand) re-cuts')
    os.utime(os.path.join(d, 'public/host/t-cut.mp4'), (t0 + 30, t0 + 30))
    check(run() == 'FRESH', 'after the re-cut the cut is reused again')
    shutil.rmtree(d, ignore_errors=True)


def test_transitions():
    print('4. transitions on joins')
    real = styles_lib.video_joins
    styles_lib.video_joins = lambda cfg: [62, 100, 103, 106, 140, 152, 153, 200]   # 100-106: joins a breath apart
    try:
        s = '{\n  "id": "t",\n  "placement": "organic"\n}\n'
        cfg = {'frames': 400, 'effects': [{'kind': 'transition', 'at': 60, 'style': 'flash'}]}
        out, _ = styles_lib.apply_overlay(s, {'name': 'Test', 'transitions': {'every_join': 'whip'}}, cfg)
    finally:
        styles_lib.video_joins = real
    ats = sorted(int(x) for x in re.findall(r'"at": (\d+)', out))
    check(ats == [100, 140, 153, 200], 'a look puts one transition per 13 frames (placed at %s)' % ats)

    node = subprocess.run(['node', '--version'], capture_output=True, text=True) if _which('node') else None
    if not node or node.returncode:
        print('  SKIP the render gate check (node is not on PATH)')
        return
    js = r'''
import { build } from 'esbuild';
const root = process.argv[1], name = process.argv[2];
const entry = `
import { validateReel } from './src/methodology/ReelConfig';
import cfg from './src/methodology/reels/${name}.config';
const tr = (at) => ({ kind: 'transition', at, style: 'whip' });
const base = (cfg.effects ?? []).filter((e) => e.kind !== 'transition');
const mid = Math.round(cfg.frames / 2);
const run = (fx) => { try { validateReel({ ...cfg, effects: [...base, ...fx] }); return 'OK'; } catch (e) { return String(e.message); } };
console.log(JSON.stringify([run([]), run([tr(mid), tr(mid + 13)]), run([tr(mid), tr(mid + 3)])]));
`;
const out = await build({ stdin: { contents: entry, resolveDir: root, loader: 'ts' }, bundle: true, platform: 'node', format: 'esm', write: false, logLevel: 'silent' });
await import('data:text/javascript;base64,' + Buffer.from(out.outputFiles[0].text).toString('base64'));
'''
    reels = os.path.join(ROOT, 'src', 'methodology', 'reels')
    names = sorted(f[:-len('.config.ts')] for f in os.listdir(reels) if f.endswith('.config.ts')) if os.path.isdir(reels) else []
    for name in names:   # any reel that validates as it is will do
        p = subprocess.run(['node', '--input-type=module', '-e', js, ROOT, name], cwd=ROOT, capture_output=True, text=True)
        try:
            base, spaced, close = json.loads(p.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            continue
        if base != 'OK':
            continue
        check(spaced == 'OK', 'the render gate takes transitions 13 frames apart (%s)' % name)
        check('under 13 frames apart' in close, 'the render gate refuses two transitions 3 frames apart (%s)' % name)
        return
    print('  SKIP the render gate check (no reel here validates yet)')


def _which(cmd):
    return any(os.access(os.path.join(p, cmd), os.X_OK) for p in os.environ.get('PATH', '').split(os.pathsep))


if __name__ == '__main__':
    if '--help' in sys.argv[1:] or sys.argv[1:2] == ['-h']:   # --help: the usage, nothing else
        print((__doc__ or '').strip() or 'usage: python3 scripts/%s' % os.path.basename(__file__))
        sys.exit(0)
    test_trims_and_breaths()
    test_make_reel_recut()
    test_transitions()
    if FAILS:
        sys.exit('test_cutter: %d FAILED' % len(FAILS))
    print('test_cutter: all passed')
