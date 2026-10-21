#!/usr/bin/env python3
"""Cut sheets: look at every visual change in a render, frame by frame.

    python3 scripts/verify_cuts.py <name> <render.mp4>        exit 1 on a FAIL

Every moment the picture changes on purpose (a picture join in the cut, a scene glide, a panel
swapping in or out, words behind the host, an insert, the second framing) gets the frame before,
the frame on, and the frame after pulled from the render. Two things come out:

  1. An automatic glitch test. A frame that differs strongly from BOTH neighbours while the two
     neighbours match each other is a one-frame glitch (a flash, a wrong frame, a doubled head
     from a cutout one frame off). FAIL.
  2. Sheets in qa/<name>/cuts/ (8 events per sheet, before | on | after) for a person or Claude to
     read for what a number can't catch.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import reel_config  # noqa: E402

FPS = 30
W, H = 90, 160            # comparison size
GLITCH = 14.0             # mean luma difference that makes a frame stand out from a neighbour
NEIGHBOURS = 0.45         # ...when the two neighbours differ by less than this share of that
FLASH = 25.0              # mean luma above (or below) both neighbours that marks a flash (or a black frame)


def gray(path, frame):
    out = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-vf', 'select=eq(n\\,%d),scale=%d:%d,format=gray' % (frame, W, H),
                          '-frames:v', '1', '-f', 'rawvideo', '-'], capture_output=True).stdout
    return out if len(out) == W * H else None


def d(a, b):
    return sum(abs(x - y) for x, y in zip(a, b)) / float(W * H)


def events(cfg, name):
    ev = {}
    def add(f, why):
        f = int(round(f))
        if 1 <= f < cfg['frames'] - 1:
            ev.setdefault(f, []).append(why)
    side = os.path.join(ROOT, 'public', os.path.splitext(cfg['src'])[0] + '.json')
    if os.path.exists(side):
        for t in json.load(open(side)).get('videoJoins', []):
            add(t * FPS, 'picture join')
    for s in cfg['scenes'][1:]:
        add(s['from'], 'scene -> %s' % s['mode'])
    for i, s in enumerate(cfg.get('swaps') or []):
        add(s['in'], 'swap %d in' % (i + 1))
        if s['out'] < cfg['frames']:
            add(s['out'], 'swap %d out' % (i + 1))
    for b in cfg.get('backText') or []:
        add(b['in'], 'back text in: %s' % b['text'])
        add(b['out'], 'back text out')
    for n in cfg.get('inserts') or []:
        add(n['in'], '%s insert in' % n['kind'])
        add(n['out'], '%s insert out' % n['kind'])
    for e in cfg.get('effects') or []:
        if e['kind'] == 'transition':
            add(e['at'], 'transition: %s' % e['style'])
            continue
        add(e['in'], 'effect in: %s' % e['kind'])
        add(e['out'], 'effect out')
    return dict(sorted(ev.items()))


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    name, out = sys.argv[1], sys.argv[2]
    cfg = reel_config.load(name)
    ev = events(cfg, name)
    qa = os.path.join(ROOT, 'qa', name, 'cuts')
    os.makedirs(qa, exist_ok=True)
    for f in os.listdir(qa):
        if f.endswith(('.png', '.jpg')):
            os.remove(os.path.join(qa, f))
    fails, rows = [], []
    for f, why in ev.items():
        fr = {n: gray(out, n) for n in range(f - 2, f + 3)}    # a glitch can sit on the change or either side of it
        for m in (f - 1, f, f + 1):
            a, b, c = fr.get(m - 1), fr.get(m), fr.get(m + 1)
            if not (a and b and c):
                continue
            ab, bc, ac = d(a, b), d(b, c), d(a, c)
            if ab > GLITCH and bc > GLITCH and ac < NEIGHBOURS * min(ab, bc):
                fails.append('frame %d (%.2fs, near %s): one frame unlike both neighbours (%.0f / %.0f vs %.0f)' % (m, m / FPS, ', '.join(why), ab, bc, ac))
                continue
            # a flash (or a black frame) can sit right on a real hard change, where the neighbours differ
            # from each other too: then the tell is brightness outside the range of both neighbours
            la, lb, lc = (sum(x) / float(W * H) for x in (a, b, c))
            if lb > max(la, lc) + FLASH or lb < min(la, lc) - FLASH:
                fails.append('frame %d (%.2fs, near %s): brightness %.0f outside its neighbours (%.0f, %.0f): a flash or a dropped frame' % (m, m / FPS, ', '.join(why), lb, la, lc))
        rows.append((f, why))
    # sheets: 8 events per sheet, each row before | on | after at 180x320
    for k in range(0, len(rows), 8):
        chunk = rows[k:k + 8]
        tiles = []
        for f, why in chunk:
            for n in (f - 1, f, f + 1):
                p = os.path.join(qa, 'f%04d.png' % n)
                subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', out, '-vf', 'select=eq(n\\,%d),scale=180:320' % n, '-frames:v', '1', p], check=True)
                tiles.append(p)
        n = len(tiles)
        inputs = sum((['-i', t] for t in tiles), [])
        layout = '|'.join('%d_%d' % ((i % 3) * 180, (i // 3) * 320) for i in range(n))
        sheet = os.path.join(qa, 'sheet-%d.jpg' % (k // 8 + 1))
        subprocess.run(['ffmpeg', '-v', 'error', '-y'] + inputs + ['-filter_complex', 'xstack=inputs=%d:layout=%s:fill=black' % (n, layout), '-q:v', '4', sheet], check=True)
    json.dump({'events': [{'frame': f, 'why': w} for f, w in rows], 'fails': fails}, open(os.path.join(qa, 'cuts.json'), 'w'), indent=1)
    print('cut sheets %s: %d visual changes checked, %d sheets in qa/%s/cuts/, %d glitch' % (name, len(rows), (len(rows) + 7) // 8, name, len(fails)))
    for x in fails:
        print('  FAIL ' + x)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
