#!/usr/bin/env python3
"""Read a reels/<name>.config.ts without executing TypeScript, and check TIMELINE LAW.

    python3 scripts/reel_config.py --validate <name>

A config body is JSON between `const cfg = ` and `} satisfies ReelConfig;` with optional
trailing // comments. Structural rules (line limits, swap fit, ...) live ONCE, in
src/methodology/ReelConfig.ts validateReel, and are run here through Node (esbuild
bundle, no TS execution risk beyond our own engine code). This file adds the rules that
need the speech: every scene change and swap edge sits in a real inter-word gap, scene
changes follow a sentence end, and no number appears on screen that was not spoken. Python 3.9 compatible.
"""
import json
import math
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPS = 30


def config_path(name):
    return os.path.join(ROOT, 'src', 'methodology', 'reels', '%s.config.ts' % name)


def _strip_comments(body):
    out = []
    for line in body.splitlines():
        in_str, esc, cut = False, False, None
        for i, ch in enumerate(line):
            if esc:
                esc = False
                continue
            if ch == '\\':
                esc = True
            elif ch == '"':
                in_str = not in_str
            elif not in_str and line[i:i + 2] == '//':
                cut = i
                break
        out.append(line if cut is None else line[:cut])
    return '\n'.join(out)


def load(name):
    src = open(config_path(name)).read()
    m = re.search(r'const cfg = (\{.*\})\s*satisfies ReelConfig;', src, re.S)
    if not m:
        raise ValueError('%s: no `const cfg = {...} satisfies ReelConfig;` block' % config_path(name))
    return json.loads(_strip_comments(m.group(1)))


def host_file(cfg, hi=False):
    """The host picture the render draws, under public/: the color-graded copy (scripts/color_lut.py) when the config
    names a color look and that copy exists, else the cut itself. hi: the full-resolution twin, or None."""
    src = cfg['src']
    base = src[:-len('-cut.mp4')] if src.endswith('-cut.mp4') else None
    graded = (cfg.get('color') or 'natural') != 'natural' and base is not None
    if hi:
        if base is None:
            return None
        for f in ([base + '-cut-hi-c.mp4'] if graded else [base + '-cut-hi.mp4']):
            if os.path.exists(os.path.join(ROOT, 'public', f)):
                return f
        return None
    if graded and os.path.exists(os.path.join(ROOT, 'public', base + '-cut-c.mp4')):
        return base + '-cut-c.mp4'
    return src


def stem(cfg):
    """The cut a reel uses: host/<stem>-cut.mp4. Variants of one cut share a stem but not a name."""
    b = os.path.basename(cfg['src'])
    return b[:-len('-cut.mp4')] if b.endswith('-cut.mp4') else os.path.splitext(b)[0]


def ts_validate(name):
    """Run the engine's own validateReel on the config (single source of structural rules)."""
    node = os.path.join(ROOT, 'scripts', 'validate_reel.mjs')
    p = subprocess.run(['node', node, name], cwd=ROOT, capture_output=True, text=True)
    return p.returncode == 0, (p.stdout + p.stderr).strip()


def timeline_errors(cfg):
    words = cfg['words']
    errs = []

    def gap_ok(frame, need_sentence_end):
        t = frame / float(FPS)
        before = [w for w in words if w['e'] <= t + 1e-6]
        after = [w for w in words if w['s'] >= t - 1e-6]
        inside = [w for w in words if w['s'] < t - 1e-6 and w['e'] > t + 1e-6]
        if inside:
            return 'lands inside the word "%s" (%.2f-%.2fs)' % (inside[0]['t'] or '?', inside[0]['s'], inside[0]['e'])
        if need_sentence_end and before:
            last = [w for w in before if w['t']]
            if last and not last[-1]['t'].rstrip('"”').endswith(('.', '?', '!')):
                return 'follows "%s", not a sentence end' % last[-1]['t']
        return None

    for i, sc in enumerate(cfg['scenes'][1:], 1):
        e = gap_ok(sc['from'], True)
        if e:
            errs.append('scene %d @%df: %s' % (i, sc['from'], e))
    # THE HOOK HOLDS (Shortify): nothing moves until the first spoken sentence ends. The open
    # zoom is allowed; a glide or a panel is not.
    first = [w for w in words if w['t'] and w['sent'] == 0]
    if first:
        hook_end = int(math.ceil(first[-1]['e'] * FPS))
        moves = [('scene %d' % i, sc['from']) for i, sc in enumerate(cfg['scenes'][1:], 1)] + \
                [('swap %d' % i, sw['in']) for i, sw in enumerate(cfg['swaps'])]
        for label, f in moves:
            if f < hook_end:
                errs.append('%s moves at %df, inside the spoken hook (ends %df): the hook holds, no cuts' % (label, f, hook_end))
    # CLAIMS GUARD: no number on screen that was not said. Panel and cover copy are free
    # text, so this is the one place a figure could slip in unspoken.
    spoken = set()
    NUMW = {'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5', 'six': '6', 'seven': '7', 'eight': '8',
            'nine': '9', 'ten': '10', 'eleven': '11', 'twelve': '12', 'fifteen': '15', 'twenty': '20', 'thirty': '30'}
    for w in words:
        spoken.update(re.findall(r'\d+', w['t']))
        bare = re.sub(r'[^a-z]', '', w['t'].lower())
        if bare in NUMW:
            spoken.add(NUMW[bare])   # "eight days" said aloud allows "8 days" on screen
    def strings(o):
        if isinstance(o, str):
            yield o
        elif isinstance(o, dict):
            for k, v in o.items():
                if k == 'source' and isinstance(v, str):
                    # a proof shot's capture date is provenance, not a claim: only the DATE is exempt,
                    # any other figure in the source line is still checked
                    yield re.sub(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.? \d{1,2},? \d{4}\b|\b\d{4}-\d{2}-\d{2}\b', '', v)
                elif k not in ('kind', 'at', 'pickAt', 'pick', 'frame', 'in', 'out', 'src', 'w', 'h', 'focus', 'x', 'y'):
                    yield from strings(v)
        elif isinstance(o, list):
            for v in o:
                yield from strings(v)
    shown = list(strings(cfg['swaps'])) + list(strings(cfg.get('cover') or {})) + [b['text'] for b in cfg.get('backText') or []]
    th = cfg.get('thumbnail') or {}
    shown += [th.get('back', ''), th.get('front', '')]
    shown += [b.get('label') or '' for b in cfg.get('inserts') or [] if b.get('kind') == 'clip']
    for e in cfg.get('effects') or []:   # every word an effect puts on screen
        shown += [str(e.get(k) or '').replace('==', '') for k in ('word', 'label', 'keys', 'text', 'value', 'title', 'url', 'headline', 'sub', 'callout', 'who', 'strap', 'keyword', 'lead')]
        shown += [str(x) for x in e.get('lines') or []] + [n.get('t', '') for n in e.get('notes') or []]
        shown += [it.get('t', '') for it in e.get('items') or []]
        if e.get('kind') == 'pie' and not e.get('value'):
            shown.append('%s%%' % e.get('pct'))
        shown += ['%s %s' % (l.get('t', ''), l.get('value') or '') for l in e.get('lines') or []]
    said = set(re.sub(r"[^a-z0-9']", '', w['t'].lower().replace('\u2019', "'")) for w in words)
    # member installs (AVS_HOME set) have no claims guard: what they put on screen is theirs to say (Chris, 2026-10-25)
    guard = not os.environ.get('AVS_HOME')
    for b in ((cfg.get('backText') or []) + ([{'text': th['back']}] if th.get('back') else [])) if guard else []:
        for t in b['text'].split():
            if re.sub(r"[^a-z0-9']", '', t.lower().replace('\u2019', "'")) not in said:
                errs.append('back text "%s": "%s" is never spoken in the reel' % (b['text'], t))
    for e in (cfg.get('effects') or []) if guard else []:
        if e.get('kind') == 'word-stamp':
            t = re.sub(r"[^a-z0-9']", '', e['word'].lower().replace('\u2019', "'"))
            if t and t not in said:
                errs.append('word-stamp "%s" is never spoken in the reel' % e['word'])
    for txt in shown if guard else []:
        for n in re.findall(r'\d+', txt):
            if n not in spoken:
                errs.append('number "%s" on screen ("%s") is never spoken in the reel' % (n, txt[:60]))
    for i, sw in enumerate(cfg['swaps']):
        for key in ('in', 'out'):
            if key == 'out' and sw['out'] >= cfg['frames']:
                continue
            e = gap_ok(sw[key], False)
            if e:
                errs.append('swap %d %s @%df: %s' % (i, key, sw[key], e))
    return errs


def main():
    if len(sys.argv) != 3 or sys.argv[1] != '--validate':
        sys.exit('usage: reel_config.py --validate <name>')
    name = sys.argv[2]
    cfg = load(name)
    ok, msg = ts_validate(name)
    errs = timeline_errors(cfg)
    print('structure (validateReel): %s%s' % ('PASS' if ok else 'FAIL', '' if ok else ' - ' + msg))
    print('timeline law: %s' % ('PASS' if not errs else 'FAIL'))
    for e in errs:
        print('  - ' + e)
    sys.exit(0 if ok and not errs else 1)


if __name__ == '__main__':
    main()
