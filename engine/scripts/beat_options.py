#!/usr/bin/env python3
"""Three versions of one storyboard beat, as short clips to watch side by side, then the pick goes into the reel.

    python3 scripts/beat_options.py <reel> <beat> --options <options.json>     render the versions
    python3 scripts/beat_options.py <reel> <beat> --pick b                     put version b into the reel

<beat> is a storyboard beat id (b03). options.json is written by Claude, two or three entries:
    [{"label": "Words behind you", "effects": [...], "backText": [...], "inserts": [...]}, ...]
Each version REPLACES what the reel has in that beat (effects, back text and inserts that overlap it) with its own
entries, which must sit inside the beat (transitions: their `at`). Writes out/drafts/<reel>-<beat>-a.mp4 (half size,
with the voice, badged DRAFT) and qa/<reel>/options-<beat>.json. The pick edits the reel's config, so the reel needs
a fresh preview, draft and approval afterwards.
"""
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import reel_config  # noqa: E402
import styles_lib as L  # noqa: E402
from storyboard import beats  # noqa: E402

LISTS = ('effects', 'backText', 'inserts')
FPS = 30


def span_of(e):
    return (e['at'], e['at'] + 1) if e.get('kind') == 'transition' else (e['in'], e['out'])


def patched(text, cfg, opt, a, b):
    """The reel's config text with the beat's effects, back text and inserts replaced by the option's."""
    for key in LISTS:
        keep = [e for e in cfg.get(key) or [] if not (span_of(e)[0] < b and a < span_of(e)[1])]
        new = keep + list(opt.get(key) or [])
        new.sort(key=lambda e: span_of(e)[0])
        text = L.set_key(text, key, new, 'beat options') if new else L.remove_key(text, key)
    return text


def check(opts, a, b):
    if not 2 <= len(opts) <= 3:
        sys.exit('beat_options: give two or three versions')
    for i, o in enumerate(opts):
        if not o.get('label'):
            sys.exit('beat_options: version %d needs a label (a few plain words)' % (i + 1))
        for key in LISTS:
            for e in o.get(key) or []:
                s, t = span_of(e)
                if s < a or t > b:
                    sys.exit('beat_options: version "%s": a %s entry runs outside the beat (%d-%d)' % (o['label'], key, a, b))


def register(ids):
    p = os.path.join(ROOT, 'src', 'methodology', 'Root.tsx')
    r = open(p).read()
    r = re.sub(r'    <Reel id="[^"]+-opt-[abc]" load=\{[^\n]*\n', '', r)
    anchor = r.index('    <Reel id=')
    lines = ''.join("    <Reel id=\"%s\" load={() => import('./reels/%s.config')} />\n" % (i, i) for i in ids)
    open(p, 'w').write(r[:anchor] + lines + r[anchor:])


def main():
    a = sys.argv[1:]
    pos = [x for i, x in enumerate(a) if not x.startswith('--') and (i == 0 or a[i - 1] not in ('--options', '--pick'))]
    if len(pos) != 2:
        sys.exit(__doc__)
    reel, beat = pos
    cfg = reel_config.load(reel)
    bt = next((x for x in beats(cfg) if x['id'] == beat), None)
    if not bt:
        sys.exit('beat_options: %s has no beat %s (beats: %s)' % (reel, beat, ', '.join(x['id'] for x in beats(cfg))))
    A, B = bt['from'], bt['to']
    rec = os.path.join(ROOT, 'qa', reel, 'options-%s.json' % beat)
    text = open(reel_config.config_path(reel)).read()

    if '--pick' in a:
        letter = a[a.index('--pick') + 1].lower()
        saved = json.load(open(rec))
        opt = next((o for o in saved['options'] if o['letter'] == letter), None)
        if not opt:
            sys.exit('beat_options: no version %s for %s %s' % (letter, reel, beat))
        open(reel_config.config_path(reel), 'w').write(patched(text, cfg, opt, A, B))
        ok, msg = reel_config.ts_validate(reel)
        if not ok:
            open(reel_config.config_path(reel), 'w').write(text)
            sys.exit('beat_options: the pick did not validate, the reel is unchanged:\n' + msg)
        print('beat_options: version %s ("%s") is in %s %s. Re-run the preview and the draft, then ask for approval again.' % (letter, opt['label'], reel, beat))
        return

    opts = json.load(open(a[a.index('--options') + 1]))
    check(opts, A, B)
    # a run that was cut off (the app quit) leaves its versions behind: clear them first
    register([])
    for letter in 'abc':
        stale = reel_config.config_path('%s-opt-%s' % (reel, letter))
        if os.path.exists(stale):
            os.remove(stale)
    ids = []
    for letter, o in zip('abc', opts):
        o['letter'] = letter
        rid = '%s-opt-%s' % (reel, letter)
        t = re.sub(r'"id": "[^"]+"', '"id": "%s"' % rid, patched(text, cfg, o, A, B), count=1)
        open(reel_config.config_path(rid), 'w').write(t)
        ids.append(rid)
    register(ids)
    os.makedirs(os.path.join(ROOT, 'out', 'drafts'), exist_ok=True)
    os.makedirs(os.path.dirname(rec), exist_ok=True)
    matte = os.environ['AVS_MATTE_PYTHON']   # runtime/env.sh sets it
    f0, f1 = max(0, A - 15), min(cfg['frames'] - 1, B + 15)
    try:
        for rid, o in zip(ids, opts):
            ok, msg = reel_config.ts_validate(rid)
            if not ok:
                sys.exit('beat_options: version "%s" does not validate:\n%s' % (o['label'], msg))
            if o.get('backText'):
                subprocess.run([matte, os.path.join(HERE, 'matte_reel.py'), rid], check=True, capture_output=True)
            pic = os.path.join(ROOT, 'out', 'drafts', rid + '-picture.mp4')
            p = subprocess.run(['npx', 'remotion', 'render', 'src/methodology/index.ts', rid, pic, '--frames=%d-%d' % (f0, f1),
                                '--scale=0.5', '--muted', '--crf=28', '--public-dir=public', '--log=error'], cwd=ROOT, capture_output=True, text=True)
            if p.returncode != 0:
                sys.exit('beat_options: render failed for "%s": %s' % (o['label'], (p.stderr or p.stdout)[-400:]))
            badge = os.path.join(ROOT, 'out', 'drafts', rid + '-badge.png')
            subprocess.run([matte, os.path.join(HERE, 'draft_badge.py'), badge, '540'], check=True)
            out = os.path.join(ROOT, 'out', 'drafts', '%s-%s-%s.mp4' % (reel, beat, o['letter']))
            src = os.path.join(ROOT, 'public', cfg['src'])
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', pic, '-ss', '%.3f' % (f0 / FPS), '-t', '%.3f' % ((f1 - f0 + 1) / FPS), '-i', src,
                            '-i', badge, '-filter_complex', '[0:v][2:v]overlay=(W-w)/2:20[v]', '-map', '[v]', '-map', '1:a:0',
                            '-c:v', 'libx264', '-crf', '28', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '96k',
                            '-shortest', '-movflags', '+faststart', out], check=True)
            for f in (pic, badge):
                os.remove(f)
            print('beat_options: %s  %s' % (os.path.relpath(out, ROOT), o['label']), flush=True)
    finally:
        register([])
        for rid in ids:
            if os.path.exists(reel_config.config_path(rid)):
                os.remove(reel_config.config_path(rid))
    json.dump({'reel': reel, 'beat': beat, 'from': A, 'to': B, 'options': opts}, open(rec, 'w'), indent=1)
    print('beat_options: send the clips into the chat with their letters and labels; on a pick run --pick <letter>')


if __name__ == '__main__':
    main()
