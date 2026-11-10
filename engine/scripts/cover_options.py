#!/usr/bin/env python3
"""Three covers for a video, side by side on the storyboard, then the pick goes into the reel.

    python3 scripts/cover_options.py <reel> --options <covers.json>     write the three and render their stills
    python3 scripts/cover_options.py <reel> --pick a|b|c                put that cover on the video
    python3 scripts/cover_options.py <reel> --status                    COVER ROW ON THE PAGE, or NO COVER ROW: why
    python3 scripts/cover_options.py <reel> --carry [--from <reel>]     the covers again after a restyle (retime_reel.py
                                                                        and make_style.py run it themselves)

covers.json is written by Claude, the covers to offer beside the one the reel has now:
    {"b": {"frame": 312, "title": "Four fees", "accent": "Four"},
     "c": {"frame": 45, "title": "Same four things", "back": "four things", "short": "four",
           "fallback": {"frame": 760, "title": "Same four things", "accent": "four"}}}
A is the cover in the config (give "a" too when the reel has none). B is a second frame with a second title from
their words. C is the same kind of cover with 1-4 of their spoken words huge behind the head ("back"), the title in
front. Words that hide behind the head don't read, so C is measured: the share of each row's letters the person
covers, from three stills (the cover, the same frame without the words, and the words with nothing in front). A row
more than HIDDEN_MAX covered fails. Then "short" (one short word) is tried, and when that fails too the third cover is
"fallback", a frame and title cover, and a line starting COVER C SWAPPED says why. A paid ad has no C with words
behind: its three are frame and title covers. A captions-only look has no title: its three are three frames
({"frame": N, "title": ""}). Every cover passes the same checks as the reel's own cover (validateReel, and outside a
member install the spoken-words and numbers checks of reel_config.py).

Writes qa/<reel>/covers.json and qa/<reel>/storyboard/covers/cover-<x>.png (full size) and .jpg (for the page), then
rebuilds the storyboard when the reel has one, with the "Your cover" row above Part 01. The covers follow the reel: a
re-cut moves their frames with the cut, a restyle judges them again by the new look (frames only on a captions-only
look, no words behind on a paid ad) and a second version in another look gets its own, all redrawn. Covers that no
longer match the reel are never shown: the row is left out, and a line starting COVERS NOT CARRIED says why. Asking for other words: write
new options and run --options again. The pick edits the reel's config (so an approval goes stale, as any change does),
cuts the cover frame for a words-behind cover, redraws the preview's frame 0, marks the pick and rebuilds the storyboard.
"""
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REMOTION = ['node', os.path.join(ROOT, 'node_modules', '@remotion', 'cli', 'remotion-cli.js')]   # never npx: on Windows npx is a .cmd file, which Python cannot start by bare name
sys.path.insert(0, HERE)
import reel_config  # noqa: E402
import styles_lib as L  # noqa: E402

LETTERS = 'abc'
HIDDEN_MAX = 0.35   # a row of words behind the head reads while the person covers no more than this share of its letters
LETTER_MAX = 0.5    # ...and no single letter more than about half hidden ("F UR" reads wrong even when the row passes)
MATTE = os.environ.get('AVS_MATTE_PYTHON', '')   # runtime/env.sh sets it (read lazily, so --help works without it)


class CoverError(Exception):
    pass


def kind_of(cfg):
    """frames: the reel's cover has no title (a captions-only look), paid or not: three frames. paid: frame and title
    covers only. regular: C has words behind."""
    if not ((cfg.get('cover') or {}).get('title') or '').strip():
        return 'frames'
    if cfg.get('placement') == 'paid':
        return 'paid'
    return 'regular'


def cut_print(cfg):
    """The cut the covers' frame numbers belong to. When it changes, only a re-cut's frame remap (retime_reel.py) can
    carry them."""
    import hashlib
    cut = os.path.join(ROOT, 'public', cfg['src'])
    st = os.stat(cut) if os.path.exists(cut) else None
    key = {'src': cfg['src'], 'size': st.st_size if st else None, 'mtime': int(st.st_mtime) if st else None, 'frames': cfg['frames']}
    return hashlib.sha1(json.dumps(key, sort_keys=True).encode()).hexdigest()[:16]


def fingerprint(cfg):
    """What the three covers were made for: the cut, the kind and what draws them (grade, color look, the look's
    back-text type). A re-cut, a restyle, a color change or a change of placement changes it: stale covers are never
    shown, they are carried (carry) or the row is left out."""
    import hashlib
    key = {'cut': cut_print(cfg), 'kind': kind_of(cfg), 'grade': cfg.get('grade'), 'color': cfg.get('color') or 'natural',
           'back': (cfg.get('look') or {}).get('backText')}
    return hashlib.sha1(json.dumps(key, sort_keys=True).encode()).hexdigest()[:16]


def record_path(reel):
    return os.path.join(ROOT, 'qa', reel, 'covers.json')


def status(reel, cfg=None):
    """(True, '') when the reel's three covers are current and can go on the storyboard, else (False, the reason)."""
    rec = record_path(reel)
    if not os.path.exists(rec):
        return False, 'no cover options yet'
    saved = json.load(open(rec))
    if saved.get('stale'):
        return False, saved['stale']
    cfg = cfg or reel_config.load(reel)
    if saved.get('fp') != fingerprint(cfg):
        return False, 'the covers were made before the cut or the look changed'
    for x in LETTERS:
        if not os.path.exists(os.path.join(ROOT, 'qa', reel, 'storyboard', 'covers', 'cover-%s.jpg' % x)):
            return False, 'a cover still is missing'
    return True, ''


def anchored(text):
    """A config from before "placement" existed gets it said out loud (organic), so the cover can be set."""
    if '\n  "placement":' not in text and '\n  "meta":' in text:
        text = text.replace('\n  "meta":', '\n  "placement": "organic",\n  "meta":', 1)
    return text


def with_cover(text, cover):
    return L.set_key(anchored(text), 'cover', cover, 'the cover (scripts/cover_options.py)')


def register(ids):
    p = os.path.join(ROOT, 'src', 'methodology', 'Root.tsx')
    r = open(p).read()
    r2 = re.sub(r'    <Reel id="[^"]+-cov-[a-z]" load=\{[^\n]*\n', '', r)
    anchor = r2.index('    <Reel id=')
    r2 = r2[:anchor] + ''.join("    <Reel id=\"%s\" load={() => import('./reels/%s.config')} />\n" % (i, i) for i in ids) + r2[anchor:]
    if r2 != r:
        open(p, 'w').write(r2)


def check(reel, cfg, opts, written=True):
    """Plain reasons the options can't be used (empty: fine)."""
    errs, kind = [], kind_of(cfg)
    for x in LETTERS:
        o = opts.get(x)
        if not isinstance(o, dict) or not isinstance(o.get('frame'), int):
            errs.append('cover %s needs a frame' % x.upper())
            continue
        if not 0 <= o['frame'] < cfg['frames']:
            errs.append('cover %s: frame %d is not in this cut (0-%d)' % (x.upper(), o['frame'], cfg['frames'] - 1))
        if x == 'a':   # cover A is the cover the reel has now, whatever kind it is
            continue
        if kind == 'frames' and (o.get('title') or o.get('back')):
            errs.append('cover %s: this look has no title, so each cover is a frame alone' % x.upper())
        if kind == 'paid' and o.get('back'):
            errs.append('cover %s: a paid ad cover is a frame and a title, no words behind' % x.upper())
        if kind == 'regular' and x == 'c' and written and not o.get('back'):
            errs.append('cover C has 1-4 of their spoken words behind the head ("back")')
        if kind == 'regular' and x == 'c' and written:   # what Claude writes for C: words behind and a fallback
            fb = o.get('fallback')
            if not isinstance(fb, dict) or not isinstance(fb.get('frame'), int) or not (fb.get('title') or '').strip() or fb.get('back'):
                errs.append('cover C needs a "fallback": a frame and title cover for when the words behind don\'t read')
            if isinstance(fb, dict) and any(isinstance(opts.get(y), dict) and fb.get('frame') == opts[y].get('frame') for y in 'ab'):
                errs.append('cover C\'s fallback needs its own frame, not one A or B has')
            if o.get('short') and len(str(o['short']).split()) != 1:
                errs.append('cover C "short" is one short word')
        if kind == 'regular' and x == 'b' and o.get('back'):
            errs.append('cover %s is a frame and a title, only C has words behind' % x.upper())
    if kind != 'frames' and opts.get('a') and opts.get('b') and opts['a'].get('title') and opts['a'].get('title') == opts['b'].get('title'):
        errs.append('cover B needs a second title, not the one A has')
    if opts.get('a') and opts.get('b') and opts['a'].get('frame') == opts['b'].get('frame'):
        errs.append('cover B needs a second frame, not the one A has')
    return errs


def guard(reel, text):
    """The reel's own checks on a cover: validateReel, then what the cover adds to the timeline law (spoken words,
    numbers), compared against the reel as it is so an older problem elsewhere is not blamed on the cover."""
    rid = reel + '-cov-x'
    path = reel_config.config_path(rid)
    open(path, 'w').write(re.sub(r'"id": "[^"]+"', '"id": "%s"' % rid, text, count=1))
    try:
        ok, msg = reel_config.ts_validate(rid)
        if not ok:
            return msg.replace(rid, reel)
        before = set(reel_config.timeline_errors(reel_config.load(reel)))
        new = [e for e in reel_config.timeline_errors(reel_config.load(rid)) if e not in before]
        return '\n'.join(new)
    finally:
        os.remove(path)


def head_top(reel_cfg, frame):
    """The top of the head in canvas px, from the cover frame's cutout (public/host/<stem>-thumb-<frame>.png)."""
    png = os.path.join(ROOT, 'public', 'host', '%s-thumb-%d.png' % (reel_config.stem(reel_cfg), frame))
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', png, '-vf', 'alphaextract,scale=270:480', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'],
                         capture_output=True).stdout
    for y in range(480):
        if sum(1 for v in raw[y * 270:(y + 1) * 270] if v > 128) >= 4:
            return y * 4
    return None


def _rgb(png):
    return subprocess.run(['ffmpeg', '-v', 'error', '-i', png, '-vf', 'scale=270:480', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                          capture_output=True, check=True).stdout


def measure(reel, cfg, text, cover):
    """How much of each row of the words behind the person hides: three stills of frame 0 (the cover, the frame
    without the words, the words with nothing in front of them: the same frame through a stand-in name whose cutout is
    empty), the letters where the last two differ, the visible letters where the first two differ. Returns the hidden
    share per row (top to bottom) and the top of the head it measured."""
    tmp = os.path.join(ROOT, 'qa', reel, 'storyboard', 'covers', '.measure')
    os.makedirs(tmp, exist_ok=True)
    probe = 'zzcovprobe-' + reel   # the words with nothing in front: the same footage under a name with an empty cutout
    pub = os.path.join(ROOT, 'public', 'host')
    link = os.path.join(pub, probe + '-cut.mp4')
    empty = os.path.join(pub, '%s-thumb-%d.png' % (probe, cover['frame']))
    ids = {k: '%s-cov-%s' % (reel, k) for k in ('m', 'p', 'q')}
    try:
        if os.path.lexists(link):
            os.remove(link)
        os.link(os.path.join(ROOT, 'public', reel_config.host_file(cfg)), link)   # a second name for the same file (the bundler skips symlinks)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=c=black@0.0:s=1080x1920,format=rgba', '-frames:v', '1', empty], check=True)
        write = lambda rid, t: open(reel_config.config_path(rid), 'w').write(re.sub(r'"id": "[^"]+"', '"id": "%s"' % rid, t, count=1))  # noqa: E731
        write(ids['m'], with_cover(text, cover))
        subprocess.run([MATTE, os.path.join(HERE, 'matte_reel.py'), ids['m']], check=True, capture_output=True)
        top = head_top(cfg, cover['frame'])
        if top is not None and 'backY' not in cover:
            cover['backY'] = min(1500, max(150, top))
        write(ids['m'], with_cover(text, cover))
        write(ids['p'], with_cover(text, {k: v for k, v in cover.items() if k not in ('back', 'backY')}))
        q = with_cover(text, cover).replace('"src": "%s"' % cfg['src'], '"src": "host/%s-cut.mp4"' % probe, 1)
        q = L.remove_key(q, 'color')   # the stand-in is the picture as drawn already
        write(ids['q'], q)
        register(list(ids.values()))
        shots = {}
        for k, rid in ids.items():
            shots[k] = os.path.join(tmp, '%s.png' % k)
            still(rid, shots[k])
        m, p, q = (_rgb(shots[k]) for k in ('m', 'p', 'q'))
    finally:
        register([])
        for rid in ids.values():
            if os.path.exists(reel_config.config_path(rid)):
                os.remove(reel_config.config_path(rid))
        for f in (link, empty, empty + '.src'):
            if os.path.lexists(f):
                os.remove(f)
        shutil.rmtree(tmp, ignore_errors=True)   # the three stills are read by now: about 8 MB a cover, never kept
    W, H = 270, 480
    def differs(a, b, i):
        return max(abs(a[i] - b[i]), abs(a[i + 1] - b[i + 1]), abs(a[i + 2] - b[i + 2])) > 40
    letters = [[differs(q, p, 3 * (y * W + x)) for x in range(W)] for y in range(H)]
    seen = [[letters[y][x] and differs(m, p, 3 * (y * W + x)) for x in range(W)] for y in range(H)]
    hidden, worst_letter = [], []
    for (a, b), text in zip(drawn_rows(cfg, cover), row_texts(cover)):   # each row where the render draws it (same words, wrap, size and place)
        a, b = max(0, int(a / 4)), min(H, int(b / 4) + 1)
        total = sum(sum(r) for r in letters[a:b])
        if total > 20:
            hidden.append(1 - sum(sum(r) for r in seen[a:b]) / float(total))
            col = [sum(letters[y][x] for y in range(a, b)) for x in range(W)]
            vis = [sum(seen[y][x] for y in range(a, b)) for x in range(W)]
            shares = [1 - sum(vis[x0:x1]) / float(sum(col[x0:x1])) for x0, x1 in letter_cells(col, text) if sum(col[x0:x1]) > 4]
            worst_letter.append(max(shares) if shares else 0.0)
    return hidden, top, worst_letter


def row_texts(cover):
    """The words-behind rows' text, as drawn_rows splits them."""
    words = (cover.get('back') or '').strip().upper().split()
    half = (len(words) + 1) // 2
    return [r for r in (' '.join(words[:half]), ' '.join(words[half:])) if r]


def letter_cells(col, text):
    """Each letter's columns in one row: the runs of inked columns when there is one run a letter, else each word's
    run (split at the widest gaps) cut evenly by its letter count (letters drawn close can touch)."""
    runs, x = [], 0
    while x < len(col):
        if col[x]:
            x0 = x
            while x < len(col) and col[x]:
                x += 1
            runs.append((x0, x))
        x += 1
    n = len(text.replace(' ', ''))
    if not runs or n == 0:
        return []
    if len(runs) == n:
        return runs
    words = text.split()
    gaps = sorted(range(len(runs) - 1), key=lambda i: runs[i + 1][0] - runs[i][1], reverse=True)[:len(words) - 1]
    spans, start = [], runs[0][0]
    for i in sorted(gaps):
        spans.append((start, runs[i][1]))
        start = runs[i + 1][0]
    spans.append((start, runs[-1][1]))
    if len(spans) != len(words):
        spans, words = [(runs[0][0], runs[-1][1])], [text.replace(' ', '')]
    cells = []
    for (x0, x1), w in zip(spans, words):
        step = (x1 - x0) / float(len(w))
        cells += [(int(x0 + i * step), max(int(x0 + i * step) + 1, int(x0 + (i + 1) * step))) for i in range(len(w))]
    return cells


FACE_WIDTH = {'anton': 0.47, 'bebas': 0.42, 'oswald': 0.5, 'archivo': 0.62, 'archivoitalic': 0.6, 'intertight': 0.55,
              'barlowcond': 0.46}   # the display faces' glyph width in em (src/components/vc/fonts.ts), a brand sans 0.56


def drawn_rows(cfg, cover):
    """The words-behind rows as Cover.tsx BehindWords draws them: (top, bottom) of each row in canvas px."""
    words = (cover.get('back') or '').strip().upper().split()
    half = (len(words) + 1) // 2
    rows = [r for r in (' '.join(words[:half]), ' '.join(words[half:])) if r]
    font = ((cfg.get('look') or {}).get('backText') or {}).get('font')
    k = FACE_WIDTH.get(font, 0.56) * 1.25 if font else 0.74
    sizes = [min(320, (cfg['source']['w'] * 0.94) / (k * max(len(r), 3))) for r in rows]
    block = sum(z * 0.92 for z in sizes)
    y = max(50, (cover.get('backY') if cover.get('backY') is not None else cfg['faceY'] - 400) - block + sizes[-1] * 0.38)
    out = []
    for z in sizes:
        out.append((y, y + z * 0.92))
        y += z * 0.92
    return out


def still(rid, out_png):
    env = dict(os.environ)
    p = subprocess.run(REMOTION + ['still', 'src/methodology/index.ts', rid, out_png, '--frame=0', '--public-dir=public', '--log=error'],
                       cwd=ROOT, capture_output=True, text=True, env=env)
    if p.returncode != 0:
        sys.exit('cover_options: could not draw %s: %s' % (rid, (p.stderr or p.stdout)[:400]))


def page_jpg(png, jpg):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', png, '-vf', 'scale=324:-2', '-q:v', '4', jpg], check=True)


def rebuild_storyboard(reel):
    if os.path.isdir(os.path.join(ROOT, 'qa', reel, 'preview')):
        subprocess.run([sys.executable, os.path.join(HERE, 'storyboard.py'), reel, '--keep-notes'], check=True)   # a cover change never archives notes not yet applied


def same(a, b):
    keys = ('frame', 'title', 'accent', 'back', 'backY')
    return bool(a) and bool(b) and all((a.get(k) or None) == (b.get(k) or None) for k in keys)


def is_c(cover, given_c):
    """The cover is one of the covers C can come out as from what Claude wrote: its words behind, its short word, or
    its fallback (the words behind are measured, so any of the three can be the one on the video)."""
    base = {k: given_c.get(k) for k in ('frame', 'title', 'accent')}
    outs = [dict(base, back=w) for w in (given_c.get('back'), given_c.get('short')) if w] + [given_c.get('fallback') or {}]
    return any(same(dict(o, backY=None), dict(cover, backY=None)) for o in outs if o)


def options(reel, file):
    """Claude's candidates: cover A is the cover the reel has now (whatever kind), B and C as written."""
    try:
        cfg = reel_config.load(reel)
        given = json.load(open(file))
        recs = {x: given[x] for x in LETTERS if x in given}
        given_c = given.get('c') if isinstance(given.get('c'), dict) else None
        kind = kind_of(cfg)
        if kind == 'paid' and given_c and given_c.get('back'):   # the same options file on a paid ad: C is its fallback
            if not given_c.get('fallback'):
                raise CoverError('cover C has words behind the head and no "fallback", and a paid ad has no words behind')
            recs['c'] = dict(given_c['fallback'])
        picked = 'a'
        if 'a' not in recs:
            if not cfg.get('cover'):
                raise CoverError('%s has no cover yet, so give "a" too' % reel)
            now = {k: v for k, v in cfg['cover'].items() if v is not None and not (kind != 'regular' and k in ('back', 'backY'))}
            hit = [x for x in 'bc' if x in recs and (same(dict(recs[x], backY=None), dict(now, backY=None))
                                                    or (x == 'c' and given_c and is_c(now, given_c)))]
            if hit:   # the cover on the video is one of the new options: that one stays picked, A is the one before
                picked = hit[0]
                old = (json.load(open(record_path(reel))).get('options') or {}).get('a') if os.path.exists(record_path(reel)) else None
                if not old and picked == 'c' and given_c:   # no record of it: C is cover A's frame and title with words added
                    old = {k: given_c[k] for k in ('frame', 'title', 'accent') if given_c.get(k) is not None}
                if not old or any(same(dict(old, backY=None), dict(recs[x], backY=None)) for x in 'bc' if x in recs):
                    raise CoverError('the cover on the video is the same as cover %s, so give "a" too (another frame and title)' % picked.upper())
                recs['a'] = {k: v for k, v in old.items() if not (kind != 'regular' and k in ('back', 'backY'))}
            else:
                recs['a'] = now
        build(reel, recs, given_c, picked, cfg)
    except CoverError as e:
        sys.exit('cover_options: %s' % e)


def build(reel, recs, given_c, picked, cfg=None, rebuild=True, keep_picked=False):
    """The three covers as their own records, the picked one marked: check them, measure C's words behind (its back,
    short, then fallback from given_c on a regular post), render the stills, write covers.json and, when the picked
    record changed (carried), put it on the reel so frame 0 shows it. Raises CoverError with a plain reason."""
    cfg = cfg or reel_config.load(reel)
    recs = json.loads(json.dumps(recs))
    # C is measured again from what Claude wrote, unless C is the one on the video: a picked cover keeps its picture
    words_c = kind_of(cfg) == 'regular' and given_c and given_c.get('back') and not (keep_picked and picked == 'c')
    errs = check(reel, cfg, dict(recs, c=given_c if words_c else recs['c']), written=bool(words_c) or not keep_picked)
    if errs:
        raise CoverError('those covers can\'t be used:\n  - ' + '\n  - '.join(errs))
    text = open(reel_config.config_path(reel)).read()
    tries = []   # C's candidates in order: the words behind, the short word, then the frame and title fallback
    if words_c:
        base = {k: v for k, v in given_c.items() if k in ('frame', 'title', 'accent')}
        tries = [dict(base, back=given_c['back'])] + ([dict(base, back=given_c['short'])] if given_c.get('short') else []) + [dict(given_c['fallback'])]
        recs['c'] = tries[0]
    for x in LETTERS:
        for o in ([recs[x]] if x != 'c' or not tries else tries):
            msg = guard(reel, with_cover(text, o))
            if msg:
                raise CoverError('cover %s does not pass the checks:\n%s' % (x.upper(), msg))
    out = os.path.join(ROOT, 'qa', reel, 'storyboard', 'covers')
    os.makedirs(out, exist_ok=True)
    if tries:
        why = []
        for o in tries[:-1]:
            o = dict(o)
            hidden, top, letter = measure(reel, cfg, text, o)
            if top is not None:
                o['backY'] = min(1500, max(150, top))
            worst = max(hidden) if hidden else 1.0
            worst_l = max(letter) if letter else 1.0
            print('cover_options: cover C "%s": the person covers %s of each row, %s of its most hidden letter' % (
                o['back'], ', '.join('%d%%' % round(100 * h) for h in hidden) or 'all', '%d%%' % round(100 * worst_l)), flush=True)
            if worst <= HIDDEN_MAX and worst_l <= LETTER_MAX:
                recs['c'] = o
                break
            why.append('"%s" is %d%% hidden behind the head' % (o['back'], round(100 * worst)) if worst > HIDDEN_MAX else
                       '"%s" has a letter %d%% hidden behind the head' % (o['back'], round(100 * worst_l)))
        else:
            recs['c'] = tries[-1]
            print('COVER C SWAPPED to the fallback (frame %d, "%s"): %s. Nothing to tell them, it is just a different third cover.'
                  % (recs['c']['frame'], recs['c']['title'], ', '.join(why)), flush=True)
    for x in LETTERS:   # A or B with words behind (an earlier pick of C): the words go on the top of the head on its frame
        if x != 'c' or not tries:
            if recs[x].get('back') and 'backY' not in recs[x]:
                hidden, top, _ = measure(reel, cfg, text, dict(recs[x]))
                if top is not None:
                    recs[x]['backY'] = min(1500, max(150, top))
    keyed = lambda o: (o.get('frame'), (o.get('title') or '').strip(), o.get('back') or '')  # noqa: E731
    if len({keyed(recs[x]) for x in LETTERS}) < 3:
        raise CoverError('two of the three covers came out the same')
    ids = ['%s-cov-%s' % (reel, x) for x in LETTERS]
    register(ids)
    try:
        for x, rid in zip(LETTERS, ids):   # every version written before any render: the bundle imports all three
            open(reel_config.config_path(rid), 'w').write(re.sub(r'"id": "[^"]+"', '"id": "%s"' % rid, with_cover(text, recs[x]), count=1))
            if recs[x].get('back'):
                subprocess.run([MATTE, os.path.join(HERE, 'matte_reel.py'), rid], check=True, capture_output=True)
        for x, rid in zip(LETTERS, ids):
            png = os.path.join(out, 'cover-%s.png' % x)
            still(rid, png)
            page_jpg(png, png[:-4] + '.jpg')
            print('cover_options: cover %s  %s%s' % (x.upper(), describe(recs[x]), '  (on the video)' if x == picked else ''), flush=True)
    finally:
        register([])
        for rid in ids:
            if os.path.exists(reel_config.config_path(rid)):
                os.remove(reel_config.config_path(rid))
    if not same(recs[picked], cfg.get('cover')):   # the reel's cover is always the picked record
        put_on(reel, recs[picked])
        cfg = reel_config.load(reel)
    keep = {'c': given_c} if given_c else {}
    json.dump({'reel': reel, 'kind': kind_of(cfg), 'fp': fingerprint(cfg), 'cut': cut_print(cfg), 'given': keep, 'options': recs, 'picked': picked},
              open(record_path(reel), 'w'), indent=1)
    if rebuild:
        rebuild_storyboard(reel)
    print('COVERS READY on the storyboard for %s. On a pick run --pick <letter>.' % reel)


def put_on(reel, cover):
    """The cover on the reel's config (checked, put back on failure), its cutout when it has words behind, and the
    preview's frame 0 redrawn so the storyboard shows it."""
    path = reel_config.config_path(reel)
    text = open(path).read()
    open(path, 'w').write(with_cover(text, cover))
    msg = guard(reel, open(path).read())
    if msg:
        open(path, 'w').write(text)
        raise CoverError('that cover did not pass the checks, the reel is unchanged:\n%s' % msg)
    if cover.get('back'):
        subprocess.run([MATTE, os.path.join(HERE, 'matte_reel.py'), reel], check=True, capture_output=True)
    f0 = os.path.join(ROOT, 'qa', reel, 'preview', 'f0000.png')
    if os.path.exists(f0):   # the preview's frame 0 is the cover
        still(reel, f0)


RECUT = 'the video was cut again, and the covers move with it when retime_reel.py runs'


def mark_stale(reel, reason, saved=None, rebuild=False):
    """The covers can't be shown now: a flag beside the records, never in place of them, so a later step that can
    carry them (retime_reel.py after a re-cut, a preview, the storyboard) still has them."""
    path = record_path(reel)
    rec = saved if saved is not None else (json.load(open(path)) if os.path.exists(path) else {'reel': reel})
    rec = dict(rec, reel=reel, stale=reason)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(rec, open(path, 'w'), indent=1)
    if reason == RECUT:   # the skill's re-cut steps: retime_reel.py is next and brings them back, nothing to write
        print('COVERS WAIT for %s: %s.' % (reel, reason))
    else:
        print('COVERS NOT CARRIED for %s: %s. Write the cover options again (cover_options.py %s --options <file>).' % (reel, reason, reel))
    if rebuild:
        rebuild_storyboard(reel)
    return False


def carry(reel, source=None, remap=None, rebuild=True):
    """After a re-cut (remap: old frame -> new), a restyle or a color change, or for a second version in another look
    (source: the reel it came from): the three cover records move with the cut and are redrawn, and the same one stays
    picked and on the video, its picture kept exactly (only moved with a re-cut). The other two are judged again by
    this reel's look and placement. When they can't be carried, the records stay with a stale flag, the row is left
    out and one line says so (COVERS NOT CARRIED)."""
    src = record_path(source or reel)
    if not os.path.exists(src):
        return False
    saved = json.load(open(src))
    cfg = reel_config.load(reel)
    kind = kind_of(cfg)
    keep = dict(saved, reel=reel) if not source else {'reel': reel, 'options': saved.get('options'), 'given': saved.get('given'),
                                                       'picked': saved.get('picked'), 'cut': saved.get('cut')}
    stale = lambda reason: mark_stale(reel, reason, keep, rebuild)  # noqa: E731
    recs = json.loads(json.dumps(saved.get('options') or {}))
    if not all(isinstance(recs.get(x), dict) for x in LETTERS):
        return stale('there are no covers to carry')
    picked = saved.get('picked') if saved.get('picked') in LETTERS else 'a'
    given_c = json.loads(json.dumps((saved.get('given') or {}).get('c') or {})) or None
    if remap is None and saved.get('cut') and saved['cut'] != cut_print(cfg) and not source:
        return stale(RECUT)
    if remap:
        for o in [recs[x] for x in LETTERS] + ([given_c, given_c.get('fallback') or {}] if given_c else []):
            if isinstance(o.get('frame'), int):
                new = remap(o['frame'])
                if new != o['frame']:
                    o.pop('backY', None)   # a new frame: the top of the head is measured again there
                o['frame'] = new
    for x in LETTERS:
        if x != picked:
            recs[x].pop('backY', None)   # the unpicked ones are drawn in this look, measured again
    if given_c:
        given_c.pop('backY', None)
    pk = recs[picked]
    if kind == 'frames' and ((pk.get('title') or '').strip() or pk.get('back')):
        return stale('the cover on the video has a title, and this look has none')
    if kind != 'frames' and not (pk.get('title') or '').strip():
        return stale('the cover on the video has no title, and this look has one')
    restore = False
    if kind == 'paid' and pk.get('back'):   # a paid ad has no words behind: the picked cover becomes its paid version
        if picked == 'c' and given_c and given_c.get('fallback'):
            recs['c'] = dict(given_c['fallback'])
        else:
            recs[picked] = {k: v for k, v in pk.items() if k not in ('back', 'backY')}
        print('COVER %s CHANGED on %s: a paid ad has no words behind the head, so cover %s is now %s. Say so in one line, '
              'it comes back if the video goes back to a regular post.' % (picked.upper(), reel, picked.upper(), describe(recs[picked])), flush=True)
        pk = recs[picked]
    elif kind == 'regular' and picked == 'c' and given_c and given_c.get('back') and not pk.get('back'):
        restore = True   # back from a paid ad (or a look without a title): C's words behind are measured again
    titled = all((recs[x].get('title') or '').strip() for x in LETTERS if x != picked)
    if kind == 'frames':   # a captions-only look: the same frames, no titles, no words behind
        cf = (given_c.get('fallback') or {}).get('frame') if given_c and given_c.get('back') else recs['c']['frame']
        for x in LETTERS:
            if x != picked:
                recs[x] = {'frame': cf if x == 'c' else recs[x]['frame'], 'title': ''}
    elif not titled:
        return stale('this look has a title and the covers had none')
    elif kind == 'paid':   # no words behind on a paid ad: C is its frame and title fallback
        for x in LETTERS:
            if x != picked:
                recs[x] = {k: v for k, v in recs[x].items() if k not in ('back', 'backY')}
        if picked != 'c' and given_c and given_c.get('back'):
            recs['c'] = dict(given_c['fallback'])
    try:
        build(reel, recs, given_c, picked, cfg, rebuild, keep_picked=not restore)   # what Claude wrote for C is kept for a later look
    except CoverError as e:
        return stale(str(e).replace('\n', ' ').replace('  - ', ''))
    if restore:
        now = json.load(open(record_path(reel)))['options']['c']
        print('COVER C CHANGED on %s: a regular post again, so cover C is %s. Say so in one line.' % (reel, describe(now)), flush=True)
    return True


def ensure(reel, rebuild=False):
    """Before the preview or the storyboard is built: stale covers are carried when they can be (a restyle, a color
    change), so no step has to remember it. A re-cut is carried by retime_reel.py, which knows how the frames moved:
    until then the records wait beside a stale flag and the row is left out."""
    if not os.path.exists(record_path(reel)):
        return
    saved = json.load(open(record_path(reel)))
    if not all(isinstance((saved.get('options') or {}).get(x), dict) for x in LETTERS):
        return
    ok, why = status(reel)
    if ok:
        return
    if saved.get('cut') and saved['cut'] != cut_print(reel_config.load(reel)):
        if not saved.get('stale'):
            mark_stale(reel, RECUT, saved)
        return
    carry(reel, rebuild=rebuild)


def describe(o):
    if not (o.get('title') or '').strip():
        return 'frame %d, no title' % o['frame']
    return 'frame %d, "%s"%s' % (o['frame'], o['title'], (', "%s" behind you' % o['back']) if o.get('back') else '')


def pick(reel, letter):
    rec = os.path.join(ROOT, 'qa', reel, 'covers.json')
    if not os.path.exists(rec):
        sys.exit('cover_options: %s has no cover options yet (run --options first)' % reel)
    saved = json.load(open(rec))
    ok, why = status(reel)
    if not ok:
        sys.exit('cover_options: the covers for %s are out of date (%s). Write the cover options again, nothing was changed.' % (reel, why))
    if letter not in saved['options']:
        sys.exit('cover_options: no cover %s for %s' % (letter.upper(), reel))
    cover = saved['options'][letter]
    cfg = reel_config.load(reel)
    kind = kind_of(cfg)
    if (kind == 'frames' and ((cover.get('title') or '').strip() or cover.get('back'))) or (kind == 'paid' and cover.get('back')):
        sys.exit('cover_options: cover %s does not fit this look, nothing was changed. Write the cover options again.' % letter.upper())
    try:
        put_on(reel, cover)
    except CoverError as e:
        sys.exit('cover_options: cover %s: %s' % (letter.upper(), e))
    saved['picked'] = letter
    saved['fp'] = fingerprint(reel_config.load(reel))
    json.dump(saved, open(rec, 'w'), indent=1)
    mark_pick_used(reel)
    rebuild_storyboard(reel)
    print('cover_options: cover %s is on %s (%s). Re-run the draft, then ask for approval again.' % (letter.upper(), reel, describe(cover)))


def mark_pick_used(reel):
    """The browser storyboard saves a cover pick as a note (qa/<reel>/storyboard/notes.json, "beat": "cover"). Once a pick
    is put on, every cover note there is marked used, so a later read of the notes never puts an older pick back on."""
    path = os.path.join(ROOT, 'qa', reel, 'storyboard', 'notes.json')
    try:
        notes = json.load(open(path))
    except (OSError, ValueError):
        return
    if not isinstance(notes, list):
        return
    hit = False
    for n in notes:
        if isinstance(n, dict) and str(n.get('beat')) == 'cover' and not n.get('used'):
            n['used'] = True
            hit = True
    if hit:
        json.dump(notes, open(path, 'w'), indent=1)


def main():
    a = sys.argv[1:]
    pos = [x for i, x in enumerate(a) if not x.startswith('--') and (i == 0 or a[i - 1] not in ('--options', '--pick', '--from'))]
    if len(pos) != 1 or not ('--options' in a or '--pick' in a or '--status' in a or '--carry' in a):
        sys.exit(__doc__)
    reel = pos[0]
    if not os.path.exists(reel_config.config_path(reel)):
        sys.exit('cover_options: no reel called %s' % reel)
    if '--status' in a:   # is a cover row on the storyboard? Say the covers part of the storyboard line only when it is
        ok, why = status(reel)
        print('COVER ROW ON THE PAGE' if ok else 'NO COVER ROW: %s' % why)
        return
    if '--carry' in a:   # the candidates again, judged by this reel's look (the restyle and re-cut tools call this)
        src = a[a.index('--from') + 1] if '--from' in a else None
        if not carry(reel, src):
            print('cover_options: no covers carried for %s' % reel)
        return
    if '--pick' in a:
        letter = a[a.index('--pick') + 1].lower()
        if letter not in LETTERS:
            sys.exit('cover_options: pick a, b or c')
        pick(reel, letter)
    else:
        options(reel, a[a.index('--options') + 1])


if __name__ == '__main__':
    if '--help' in sys.argv[1:] or sys.argv[1:2] == ['-h']:   # --help: the usage, nothing else
        print((__doc__ or '').strip() or 'usage: python3 scripts/%s' % os.path.basename(__file__))
        sys.exit(0)
    main()
