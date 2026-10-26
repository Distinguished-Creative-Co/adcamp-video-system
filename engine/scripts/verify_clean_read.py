#!/usr/bin/env python3
"""Leftover-flub check on the cut's own transcript (what was said, not the script).

    python3 scripts/verify_clean_read.py <cut-wx.json> <plan.json>

Two fingerprints of a mistake the cutter missed: the same run of words said twice within a
few seconds, and a "reset" cue word still in the audio. Each finding is reported against the
plan beat it falls in. Exit 0 when clean, 1 when anything was found.
Library use: scene_map.py imports norm() and find_repeats().
"""
import json
import re
import sys

MINLEN = 4       # this many consecutive matching words count as a repeat
WINDOW = 12.0    # the second saying must start within this many seconds of the first


def norm(w):
    return re.sub(r'[^a-z0-9]', '', w.lower())


def find_repeats(toks):
    """toks: [(norm, start, raw), ...] in time order. Returns repeated phrases."""
    n = len(toks)
    found = []
    covered = set()
    for i in range(n):
        if i in covered:
            continue
        best_len, best_j = 0, None
        j = i + MINLEN
        while j < n and toks[j][1] - toks[i][1] <= WINDOW:
            run = 0
            while i + run < j and j + run < n and toks[i + run][0] == toks[j + run][0]:
                run += 1
            if run >= MINLEN and run > best_len:
                best_len, best_j = run, j
            j += 1
        if best_j is None:
            continue
        found.append({'phrase': ' '.join(t[2] for t in toks[i:i + best_len]),
                      't1': toks[i][1], 't2': toks[best_j][1]})
        covered.update(range(i, best_j + best_len))
    return found


def load_beats(path):
    with open(path) as f:
        data = json.load(f)
    return data['beats'] if isinstance(data, dict) else data


def beat_of(t, beats):
    for i, b in enumerate(beats):
        lo = b['start']
        hi = lo + b['dur']
        if lo - 1e-6 <= t < hi:
            return i
    return len(beats) - 1 if beats else 0


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(args) < 2:
        sys.exit('usage: verify_clean_read.py <cut-wx.json> <plan.json>')
    with open(args[0]) as f:
        words = json.load(f)
    beats = load_beats(args[1])
    toks = [(norm(w['word']), float(w['start']), w['word'].strip()) for w in words if norm(w['word'])]
    repeats = find_repeats(toks)
    cues = [(t[1], t[2]) for t in toks if t[0] == 'reset']
    if not repeats and not cues:
        print('clean read: no repeated phrases and no leftover reset cues in the cut audio')
        return 0
    print('WARNING: the cut audio still carries what looks like an uncut flub:')
    for r in repeats:
        print('  beat %d: phrase repeated @%.2fs then @%.2fs: "%s"' % (beat_of(r['t1'], beats), r['t1'], r['t2'], r['phrase']))
    for t, raw in cues:
        print('  beat %d: leftover reset cue @%.2fs ("%s")' % (beat_of(t, beats), t, raw))
    print('fix: re-cut the source so only the clean re-read survives, then re-align and re-check')
    return 1


if __name__ == '__main__':
    sys.exit(main())
