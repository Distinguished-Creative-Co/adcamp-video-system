#!/usr/bin/env python3
"""Every effect kind in one reel, retired ones included, every optional field set: the checks must read them all.

    python3 scripts/test_effect_kinds.py [<base reel>]

Builds a throwaway copy (zz-kinds-test) of a full-frame reel (the sample in a full-frame look by default: sample, else
zz-avs-sample-clean-talk), places one of every effect kind on it in turn, then runs validateReel and the timeline law
(reel_config.py --validate) and the scene map, once as a member install (AVS_HOME set) and once without. A video made
on an older version may hold any of these, so none may crash a check. Everything it makes is removed afterwards and
Root.tsx is left as it was (the scene map needs no registration).
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import reel_config  # noqa: E402
import styles_lib as L  # noqa: E402

NAME = 'zz-kinds-test'
PROOF = {'src': 'proof/kinds-test.png', 'w': 1080, 'h': 1600, 'source': 'a test capture, 2026-11-09'}


def kinds(join_free):
    """(kind, length in frames, fields) for every kind, optional fields set. join_free(a, b): no picture join in a-b."""
    return [
        ('word-stamp', 40, {'word': 'website', 'tilt': -4}),
        ('giant-captions', 45, {}),
        ('icon-strike', 45, {'icon': 'globe', 'label': 'one fee', 'strikeAt': 20}),
        ('page-scroll', 60, dict(PROOF, url='example.com')),
        ('live-markup', 60, dict(PROOF, mark={'shape': 'circle', 'x': 60, 'y': 110, 'w': 500, 'h': 70}, markAt=15)),
        ('keycaps', 45, {'keys': 'SITE'}),
        ('receipt', 60, {'title': 'One fee', 'lines': [{'t': 'One fee', 'value': '4', 'at': 10}, {'t': 'All the edits', 'at': 30}]}),
        ('intertitle', 45, {'text': 'Same four things'}),
        ('counter', 45, {'value': '4', 'label': 'different chiropractors'}),
        ('pie', 45, {'pct': 100, 'value': '4', 'label': 'pay every month'}),
        ('list-tracker', 60, {'title': 'Same four things', 'items': [{'t': 'Pay every month', 'at': 10}, {'t': "Can't say for what", 'at': 30}]}),
        ('snap-zoom', 45, {'at': 20, 'scale': 1.15}),
        ('quote-card', 45, {'text': 'It does not have to work this way.', 'who': 'Four chiropractors'}),
        ('pinned-line', 60, {'text': 'DM me SITE', 'y': 300, 'point': 'down'}),
        ('cover-story', 60, {'title': 'Same four things', 'lines': ['One fee', 'No retainer'], 'strap': 'what they told me'}),
        ('highlighter', 60, dict(PROOF, mark={'x': 60, 'y': 246, 'w': 600, 'h': 36}, markAt=15)),
        ('note-wall', 60, {'notes': [{'t': 'The domain', 'at': 10}, {'t': 'The website', 'at': 30}], 'y': 500}),
        ('arrow-note', 45, {'text': 'Super Dad', 'x': 900, 'y': 400, 'noteY': 700}),
        ('comment-box', 45, {'keyword': 'SITE', 'lead': 'DM me'}),
        ('giant-number', 30, {'value': '4'}),
        ('lights-down', 60, {'depth': 0.6}),
        ('card', 60, {'layout': 'content', 'label': 'What I do instead', 'headline': '==One fee.==', 'sub': 'All the edits',
                      'items': [{'t': 'One fee', 'at': 10}, {'t': 'All the edits', 'at': 30}], 'list': 'check', 'callout': 'Four of them',
                      'theme': 'ink'}),
    ]


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else next((b for b in ('sample', 'zz-avs-sample-clean-talk') if os.path.exists(reel_config.config_path(b))), None)
    if not base:
        sys.exit('test_effect_kinds: no base reel (give one)')
    cfg = reel_config.load(base)
    if any(sc['mode'] != 'full' for sc in cfg['scenes']):
        sys.exit('test_effect_kinds: %s has panels; give a full-frame reel' % base)
    side = os.path.join(ROOT, 'public', os.path.splitext(cfg['src'])[0] + '.json')
    joins = [round(t * 30) for t in json.load(open(side)).get('videoJoins', [])] if os.path.exists(side) else []
    busy = [(b['in'], b['out']) for b in cfg.get('backText') or []] + [(e['at'] - 1, e['at'] + 1) for e in cfg.get('effects') or [] if e['kind'] == 'transition']
    join_free = lambda a, b: not any(a < j < b for j in joins) and not any(a < y and x < b for x, y in busy)  # noqa: E731
    fx, cur = [], 100
    for kind, n, f in kinds(join_free):
        start = cur
        while not join_free(start, start + n + 4):   # every effect clear of the hook title, transitions and picture joins
            start += 5
        if start + n >= cfg['frames'] - 10:
            sys.exit('test_effect_kinds: %s is too short to hold every kind' % base)
        e = dict({'kind': kind, 'in': start, 'out': start + n}, **json.loads(json.dumps(f)))
        for fld in ('strikeAt', 'markAt', 'at'):
            if fld in e:
                e[fld] += start
        for lst in ('items', 'lines', 'notes'):
            for it in e.get(lst) or []:
                if isinstance(it, dict) and 'at' in it:
                    it['at'] += start
        fx.append(e)
        cur = start + n + 6
    text = open(reel_config.config_path(base)).read().replace('"id": "%s"' % base, '"id": "%s"' % NAME, 1)
    text = L.remove_key(text, 'effects')
    text = L.add_effects(text, [e for e in cfg.get('effects') or [] if e['kind'] == 'transition'] + fx, 'every kind')
    made = [reel_config.config_path(NAME)] + [os.path.join(ROOT, 'script', NAME + s) for s in ('-scene-map.md', '-post.md', '-ad.md')]
    proof = os.path.join(ROOT, 'public', 'proof', 'kinds-test.png')
    fails = []
    try:
        open(reel_config.config_path(NAME), 'w').write(text)
        os.makedirs(os.path.dirname(proof), exist_ok=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=c=white:s=1080x1600', '-frames:v', '1', proof], check=True)
        for mode, env in (('member', dict(os.environ, AVS_HOME=os.environ.get('AVS_HOME') or ROOT)), ('owner', {k: v for k, v in os.environ.items() if k != 'AVS_HOME'})):
            for cmd in (['reel_config.py', '--validate', NAME], ['scene_map.py', NAME]):
                p = subprocess.run([sys.executable, os.path.join(HERE, cmd[0])] + cmd[1:], cwd=ROOT, env=env, capture_output=True, text=True)
                out = p.stdout + p.stderr
                if 'Traceback' in out or (cmd[0] == 'reel_config.py' and 'structure (validateReel): PASS' not in out):
                    fails.append('%s, %s: %s' % (mode, cmd[0], out.strip()[-400:]))
                else:
                    print('  ok %-6s %-15s %s' % (mode, cmd[0], next((l.strip() for l in out.splitlines() if 'Status' in l or 'structure' in l), 'ran')))
    finally:
        for f in made + [proof]:
            if os.path.exists(f):
                os.remove(f)
        shutil.rmtree(os.path.join(ROOT, 'qa', NAME), ignore_errors=True)   # the scene map's face check and seam record
    print('test_effect_kinds: %d kinds on %s, retired ones included' % (len(fx), base))
    if fails:
        print('FAIL (%d)' % len(fails))
        for f in fails:
            print('  - ' + f)
        sys.exit(1)
    print('PASS: validate and the scene map read every kind with every field, as a member install and without')


if __name__ == '__main__':
    if '--help' in sys.argv[1:] or sys.argv[1:2] == ['-h']:   # --help: the usage, nothing else
        print((__doc__ or '').strip() or 'usage: python3 scripts/%s' % os.path.basename(__file__))
        sys.exit(0)
    main()
