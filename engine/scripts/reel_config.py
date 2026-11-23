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
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPS = 30

# Words that flip what follows them. Words pulled from a line onto the screen keep one said just before them: "don't
# skip this" shown as SKIP THIS says the opposite (Chris, 2026-11-23). Compared after the apostrophe check folds a curly
# one to straight, and with none at all ("dont"), since transcripts and scripts spell it either way.
NEGATIONS = {'not', 'no', 'never', 'nobody', 'nothing', 'none', 'nowhere', 'neither', 'nor', 'without', 'cannot'} | {
    n + t for n in ('don', 'doesn', 'didn', 'can', 'won', 'wouldn', 'shouldn', 'couldn', 'isn', 'aren', 'wasn', 'weren',
                    'haven', 'hasn', 'hadn', 'ain', 'mustn', 'needn') for t in ("'t", 't')}
# small words that may sit between a negation and what it flips: "not a sales pitch", "never going to miss"
NEG_BRIDGE = {'a', 'an', 'the', 'to', 'be', 'my', 'your', 'our', 'their', 'his', 'her', 'its', 'this', 'that', 'these',
              'those', 'so', 'really', 'very', 'just', 'even', 'ever', 'going', 'gonna', 'want', 'wanna', 'have', 'got',
              'gotta', 'need', 'any', 'more', 'much', 'all', 'too', 'some', 'get'}


def negation_before(prev):
    """The negation that flips the words right after `prev` (the same sentence's words before them, normalized), or None.
    Walks back over at most four small bridge words ("not a", "not going to want to")."""
    for hop, t in enumerate(reversed(prev)):
        if t in NEGATIONS:
            return t
        if t not in NEG_BRIDGE or hop >= 4:
            return None
    return None


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
        # lines: a receipt's are objects ({"t", "value", "at"}), a cover story's are plain strings: read either, and
        # never a frame number ("at") as words on screen
        txt = lambda x: x if isinstance(x, str) else '%s %s' % (x.get('t', ''), x.get('value') or '') if isinstance(x, dict) else str(x)  # noqa: E731
        shown += [txt(x) for x in e.get('lines') or []] + [txt(n) for n in e.get('notes') or []]
        shown += [txt(it) for it in e.get('items') or []]
        if e.get('kind') == 'pie' and not e.get('value'):
            shown.append('%s%%' % e.get('pct'))
    # a word's key: curly apostrophe made straight, accents folded (é -> e), so Héctor on screen meets Hector said
    said_key = lambda t: re.sub(r"[^a-z0-9']", '', ''.join(c for c in unicodedata.normalize('NFKD', t) if not unicodedata.combining(c)).lower().replace('\u2019', "'"))  # noqa: E731
    said = set(said_key(w['t']) for w in words)
    # member installs (AVS_HOME set) have no claims guard: what they put on screen is theirs to say (Chris, 2026-10-25)
    guard = not os.environ.get('AVS_HOME')
    cvb = (cfg.get('cover') or {}).get('back')   # a cover's words behind the host are spoken words, like back text
    for b in ((cfg.get('backText') or []) + ([{'text': th['back']}] if th.get('back') else []) + ([{'text': cvb}] if cvb else [])) if guard else []:
        for t in b['text'].split():
            if said_key(t) not in said:
                errs.append('back text "%s": "%s" is never spoken in the reel' % (b['text'], t))
    for e in (cfg.get('effects') or []) if guard else []:
        if e.get('kind') == 'word-stamp':
            t = said_key(e['word'])
            if t and t not in said:
                errs.append('word-stamp "%s" is never spoken in the reel' % e['word'])
    for txt in shown if guard else []:
        for n in re.findall(r'\d+', txt):
            if n not in spoken:
                errs.append('number "%s" on screen ("%s") is never spoken in the reel' % (n, txt[:60]))
    # A GLASS WORD NEEDS A DARKER ROOM: frosted white on a light wall barely shows (measured 2026-11-23: a white wall
    # reads about 200-220 of 255 beside the head, a dim office about 70). The solid word, with its dark edge, reads on
    # both. Sampled beside the host (the outer columns of the words' band), where the wall shows.
    cut = os.path.join(ROOT, 'public', cfg['src'])
    for b in [b for b in cfg.get('backText') or [] if b.get('glass')] if os.path.exists(cut) else []:
        size = min(330.0, 1080 * 0.9 / (0.74 * max(len(b['text']), 3)))
        cy = b.get('y') or (1920 * 0.075 + size * 0.46)   # BackText.tsx: the row's top at 7.5% of the height, unless y
        y0, y1 = int(max(0, cy - size * 0.45) / 10), int(min(1920, cy + size * 0.45) / 10)
        lum = []
        for f in (b['in'] + 10, (b['in'] + b['out']) // 2, b['out'] - 10):
            raw = subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-i', cut, '-vf', 'select=eq(n\\,%d),scale=108:192,format=gray' % f,
                                  '-frames:v', '1', '-f', 'rawvideo', '-'], capture_output=True).stdout
            if len(raw) == 108 * 192 and y1 > y0:
                rows = [raw[r * 108:(r + 1) * 108] for r in range(y0, y1)]
                lum += [v for row in rows for v in row[:30] + row[78:]]
        if lum and sum(lum) / len(lum) > 165:
            errs.append('glass word "%s" sits on a light wall (brightness %d of 255 beside the head): frosted glass barely '
                        'shows there. Use the solid word (drop "glass")' % (b['text'], sum(lum) / len(lum)))
    # A WORD ON SCREEN KEEPS ITS "NOT" (members too: this is the meaning, not a claim). Words pulled from a line onto the
    # screen never drop a negation said just before them: "don't skip this" shown as SKIP THIS says the opposite.
    seq = [(said_key(w['t']), w['s'], w['sent']) for w in words if w['t'] and said_key(w['t'])]
    pulled = [('back text', b['text'], b['in']) for b in cfg.get('backText') or []]
    if th.get('back'):
        pulled.append(('the cover image\'s words behind', th['back'], th.get('frame', 0)))
    if cvb:
        pulled.append(('the cover\'s words behind', cvb, (cfg.get('cover') or {}).get('frame', 0)))
    for e in cfg.get('effects') or []:
        if e.get('kind') == 'word-stamp':
            pulled.append(('word stamp', e.get('word') or '', e['in']))
        elif e.get('kind') in ('intertitle', 'quote-card', 'pinned-line'):
            pulled.append((e['kind'], e.get('text') or '', e['in']))
    for label, text, frame in pulled:
        toks = [said_key(t) for t in text.replace('==', '').split() if said_key(t)]
        if not toks or any(t in NEGATIONS for t in toks):
            continue
        n = len(toks)
        hits = [i for i in range(len(seq) - n + 1) if [s[0] for s in seq[i:i + n]] == toks] or \
               [i for i, s in enumerate(seq) if s[0] == toks[0]]   # words skipped inside: anchor on the first one
        if not hits:
            continue
        i = min(hits, key=lambda k: abs(seq[k][1] - frame / float(FPS)))   # where it was said, nearest its frame
        neg = negation_before([s[0] for s in seq[:i] if s[2] == seq[i][2]])
        if neg:
            errs.append('%s "%s" leaves out "%s", said just before it: on screen it says the opposite of the line. '
                        'Put "%s" in, or pick other words' % (label, text, neg, neg.upper()))
    # lights-down stays inside one take: the picture joins live in the cut's sidecar, which validateReel only sees at render
    side = os.path.join(ROOT, 'public', os.path.splitext(cfg['src'])[0] + '.json')
    joins = [int(round(t * FPS)) for t in json.load(open(side)).get('videoJoins', [])] if os.path.exists(side) else []
    for i, e in enumerate(cfg.get('effects') or []):
        if e.get('kind') == 'lights-down':
            j = next((f for f in joins if e['in'] < f < e['out']), None)
            if j is not None:
                errs.append('lights-down %d-%df runs across the picture join at frame %d: keep it inside one take' % (e['in'], e['out'], j))
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
    if '--help' in sys.argv[1:] or sys.argv[1:2] == ['-h']:   # --help: the usage, nothing else
        print((__doc__ or '').strip() or 'usage: python3 scripts/%s' % os.path.basename(__file__))
        sys.exit(0)
    main()
