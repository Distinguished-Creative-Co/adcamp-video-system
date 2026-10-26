#!/usr/bin/env python3
"""A time in the draft (the cut) -> the same moment in the original recording, for --trim A-B.

    python3 scripts/cut_to_raw.py <name> <seconds in the draft> [<seconds> ...]

Members give notes by draft time ("at 0:24 I fumbled"). The trim works in raw seconds. This finds the words spoken
at that draft time in the cut's transcript (script/word-timings/<name>-cut-wx.json), matches them to the original
recording's transcript (<name>-wx.json) by text, inside the takes the cut kept (script/<name>-takes.md), and prints the raw time with the words around it, so the trim can
be set inside the pause next to the fumble. Times may be seconds (24.5) or minutes:seconds (0:24.5).
"""
import difflib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
norm = lambda t: re.sub(r"[^a-z0-9']", '', t.lower())  # noqa: E731


def words(path):
    d = json.load(open(path))
    d = d['words'] if isinstance(d, dict) else d
    return [w for w in d if 'start' in w and norm(w['word'])]


def secs(x):
    m = re.fullmatch(r'(?:(\d+):)?(\d+(?:\.\d+)?)', x.strip())
    if not m:
        sys.exit('cut_to_raw: %s is not a time (use 24.5 or 0:24.5)' % x)
    return int(m.group(1) or 0) * 60 + float(m.group(2))


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    name = sys.argv[1]
    wt = os.path.join(ROOT, 'script', 'word-timings')
    cut, raw = words(os.path.join(wt, '%s-cut-wx.json' % name)), words(os.path.join(wt, '%s-wx.json' % name))
    # only the takes the cut kept: a retaken line says the same words in a dropped take too
    rep_path = os.path.join(ROOT, 'script', '%s-takes.md' % name)
    kept = [(float(a), float(b)) for a, b in re.findall(r'\|\s*([\d.]+)-([\d.]+)\s*\|\s*KEPT', open(rep_path).read())] \
        if os.path.exists(rep_path) else []
    if kept:
        raw = [w for w in raw if any(a - 0.3 <= w['start'] <= b + 0.3 for a, b in kept)]
    sm = difflib.SequenceMatcher(a=[norm(w['word']) for w in cut], b=[norm(w['word']) for w in raw], autojunk=False)
    cmap = {}
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            cmap[blk.a + k] = blk.b + k
    for x in sys.argv[2:]:
        t = secs(x)
        i = min(range(len(cut)), key=lambda k: 0 if cut[k]['start'] <= t <= cut[k]['end'] else min(abs(cut[k]['start'] - t), abs(cut[k]['end'] - t)))
        j = cmap.get(i)
        if j is None:   # the nearest matched word instead
            near = sorted(cmap, key=lambda k: abs(k - i))
            if not near:
                sys.exit('cut_to_raw: the cut and the recording share no words')
            i = near[0]
            j = cmap[i]
        ctx = ' '.join(w['word'] for w in raw[max(0, j - 4):j + 5])
        print('draft %.2fs -> recording %.2fs ("%s" at %.2f-%.2f)   around it: %s'
              % (t, raw[j]['start'], cut[i]['word'], raw[j]['start'], raw[j]['end'], ctx))


if __name__ == '__main__':
    main()
