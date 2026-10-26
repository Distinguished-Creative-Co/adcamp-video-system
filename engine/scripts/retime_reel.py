#!/usr/bin/env python3
"""Move a reel's timed choices onto a new cut's word timing (after a trim or re-cut), keeping
every approved choice: scenes, swaps, panel cues, cover, thumbnail, words behind, inserts, effects and zoom punches. No regeneration, so no copy is lost.

    python3 scripts/retime_reel.py <name> --from <config backup> [--words-from <reel>]

Words come from the reel named by --words-from (default <name>), which must already be
regenerated for the new cut. Each frame is mapped through the word it sat on or the gap it sat
in, matched by text between the old and new transcripts. Then run reel_config.py --validate.
"""
import difflib
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import reel_config  # noqa: E402
import gen_reel_config  # noqa: E402
import styles_lib  # noqa: E402

FPS = 30


def load_path(path):
    src = open(path).read()
    m = re.search(r'const cfg = (\{.*\})\s*satisfies ReelConfig;', src, re.S)
    return json.loads(reel_config._strip_comments(m.group(1)))


def main():
    a = sys.argv[1:]
    name = a[0]
    old = load_path(a[a.index('--from') + 1])
    words_from = a[a.index('--words-from') + 1] if '--words-from' in a else name
    new_ref = reel_config.load(words_from)
    ow = [w for w in old['words'] if w['t']]
    nw = [w for w in new_ref['words'] if w['t']]
    key = lambda w: re.sub(r'[^a-z0-9]', '', w['t'].lower())  # noqa: E731
    sm = difflib.SequenceMatcher(a=[key(w) for w in ow], b=[key(w) for w in nw], autojunk=False)
    omap = {}
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            omap[blk.a + k] = blk.b + k
    frames_new = new_ref['frames']

    def remap(f):
        if f is None:
            return f
        if f >= old['frames']:
            return frames_new
        t = f / float(FPS)
        for i, w in enumerate(ow):                       # inside a word: same relative point
            if w['s'] <= t <= w['e'] and i in omap:
                n = nw[omap[i]]
                r = (t - w['s']) / max(w['e'] - w['s'], 1e-3)
                return int(round((n['s'] + r * (n['e'] - n['s'])) * FPS))
        prev = max([i for i, w in enumerate(ow) if w['e'] <= t and i in omap] or [-1])
        if prev < 0:
            return f
        n0 = nw[omap[prev]]
        nxt = [nw[omap[i]] for i in range(prev + 1, len(ow)) if i in omap]
        lo = n0['e'] + 0.02
        hi = nxt[0]['s'] if nxt else frames_new / float(FPS)
        tt = min(max(n0['e'] + (t - ow[prev]['e']), lo), hi)
        fr = int(round(tt * FPS))
        while fr / float(FPS) > hi and fr > 0:          # never onto the next word
            fr -= 1
        while fr / float(FPS) < n0['e']:                 # never back inside the previous one
            fr += 1
        if fr / float(FPS) > hi + 1e-9:
            # the gap is narrower than a frame: use the next gap that can hold one
            seq = [w for w in nw if w['s'] >= n0['s']]
            for w0, w1 in zip(seq, seq[1:]):
                g = int(math.ceil(w0['e'] * FPS))
                if g / float(FPS) <= w1['s'] + 1e-9:
                    return g
        return fr

    for i, j in omap.items():   # the key words (and emphasis) they chose stay on the same words in the new cut
        for flag in ('key', 'big'):
            if ow[i].get(flag):
                nw[j][flag] = True
    cfg = dict(old)
    cfg['words'] = new_ref['words']
    cfg['frames'] = frames_new
    cfg['meta'] = dict(old['meta'], cutWx=new_ref['meta']['cutWx'])
    cfg['scenes'] = [dict(sc, **({'from': remap(sc['from'])} if sc['from'] else {})) for sc in old['scenes']]
    sw_new = []
    for s in old['swaps']:
        s = json.loads(json.dumps(s))
        s['in'] = remap(s['in'])
        s['out'] = remap(s['out'])
        k = s['content']
        for fld in ('at', 'pickAt'):
            if fld in k:
                k[fld] = remap(k[fld])
        for lst in ('items', 'stages', 'options'):
            for it in k.get(lst, []):
                it['at'] = remap(it['at'])
        sw_new.append(s)
    cfg['swaps'] = sw_new
    if cfg.get('cover'):
        cfg['cover'] = dict(cfg['cover'], frame=min(remap(cfg['cover']['frame']), frames_new - 1))
    if cfg.get('thumbnail'):
        cfg['thumbnail'] = dict(cfg['thumbnail'], frame=min(remap(cfg['thumbnail']['frame']), frames_new - 1))

    def remap_timed(e):   # words behind, inserts and effects: their own frames and every timed element inside
        e = json.loads(json.dumps(e))
        for fld in ('in', 'out', 'at', 'strikeAt'):
            if isinstance(e.get(fld), (int, float)):
                e[fld] = remap(e[fld])
        for lst in ('items', 'lines', 'notes'):
            for it in e.get(lst) or []:
                if isinstance(it, dict) and isinstance(it.get('at'), (int, float)):
                    it['at'] = remap(it['at'])
        return e
    for key in ('backText', 'inserts', 'effects', 'zooms'):
        if cfg.get(key):
            cfg[key] = [remap_timed(e) for e in cfg[key]]
    # write_config knows the generator's own keys only: write those, then put back every other key the reel had
    # (look, music, words behind, effects, thumbnail...), and drop the generator keys the reel had removed
    known = ('id', 'src', 'source', 'faceX', 'faceY', 'fps', 'frames', 'open', 'scenes', 'cover', 'framing',
             'captionStyle', 'placement', 'post', 'swaps', 'words', 'meta')
    gen_reel_config.write_config(dict({k: None for k in ('cover', 'framing')}, **cfg), reel_config.config_path(name), cfg['words'])
    out = open(reel_config.config_path(name)).read()
    for k in ('framing',):
        if k not in old:
            out = styles_lib.remove_key(out, k)
    for k, v in cfg.items():
        if k not in known:
            out = styles_lib.set_key(out, k, v, 'kept by retime_reel.py')
    open(reel_config.config_path(name), 'w').write(out)
    head = '// RETIMED by scripts/retime_reel.py onto the current cut. Choices kept from the approved config.\n'
    p = reel_config.config_path(name)
    src = open(p).read().replace("import type { ReelConfig } from '../ReelConfig';\n", "import type { ReelConfig } from '../ReelConfig';\n" + head, 1)
    open(p, 'w').write(src)
    print('retimed %s: %d -> %d frames; scenes %s; swaps %s' % (
        name, old['frames'], frames_new, [s['from'] for s in cfg['scenes']], [(s['in'], s['out']) for s in cfg['swaps']]))


if __name__ == '__main__':
    main()
