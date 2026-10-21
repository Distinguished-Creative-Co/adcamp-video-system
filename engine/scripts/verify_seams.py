#!/usr/bin/env python3
"""Seam check on a cut: dead air or stray sound at its joins, head and tail.

    python3 scripts/verify_seams.py <name>

Reads public/host/<stem>-cut.mp4, its whisperX words (script/word-timings/<stem>-cut-wx.json)
and, when present, the keep list in <stem>-takes.json (to know where the joins sit in cut
time). Every pause of MIN_GAP or more between words is measured. Long air or a loud sound
at a cut join FAILS; the same in a natural pause is only a warning or a note, because a
natural pause is never cut. Reviewed exceptions live in <stem>-seams-reviewed.json.
Writes qa/<name>/seams.json. Exit 1 on any FAIL.
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import reel_config  # noqa: E402

MIN_GAP = 0.3       # pauses at least this long are checked
MAX_GAP = 0.6       # longer than this is dead air at a join
JUNK_DB = -30.0     # a peak above this inside a pause is a sound, not room tone
HEAD_MAX = 0.3      # air allowed before the first word
TAIL_MAX = 0.35     # air allowed after the last word
EDGE_AFTER = 0.10   # skip this much after the word before a pause (its release)
EDGE_BEFORE = 0.12  # and this much before the next word (its onset)


def duration_of(path):
    res = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                          '-of', 'default=noprint_wrappers=1:nokey=1', path],
                         capture_output=True, text=True, check=True)
    return float(res.stdout.strip().splitlines()[0])


def peak_db(src, a, b):
    if b - a < 0.04:
        return -120.0
    res = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', src,
                          '-af', 'atrim=%.3f:%.3f,astats=metadata=1' % (a, b), '-f', 'null', '-'],
                         capture_output=True, text=True)
    peaks = []
    for v in re.findall(r'Peak level dB:\s*(-?inf|-?\d+(?:\.\d+)?)', res.stderr):
        try:
            peaks.append(float(v))
        except ValueError:
            continue
    return max(peaks) if peaks else -120.0


def load_reviewed(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        entries = json.load(f)
    for k, r in enumerate(entries):
        if not isinstance(r.get('a'), (int, float)) or not isinstance(r.get('b'), (int, float)) or not r.get('why'):
            sys.exit('verify_seams: %s entry %d needs numeric "a" and "b" and a "why"' % (path, k))
    return entries


def join_times(takes_path):
    if not os.path.exists(takes_path):
        return []
    with open(takes_path) as f:
        keep = json.load(f)['keep']
    joins, acc = [], 0.0
    for s, e in keep[:-1]:
        acc += e - s
        joins.append(acc)
    return joins


def _join_inside(joins, gap_lo, gap_hi, slack=0.05):
    """True when a cut join falls in the pause, allowing `slack` either side."""
    lo, hi = gap_lo - slack, gap_hi + slack
    return any(lo <= t <= hi for t in joins)


def main():
    if len(sys.argv) != 2:
        sys.exit('usage: verify_seams.py <name>')
    name = sys.argv[1]
    stem = reel_config.stem(reel_config.load(name)) if os.path.exists(reel_config.config_path(name)) else name
    wt = os.path.join(ROOT, 'script', 'word-timings')
    cut = os.path.join(ROOT, 'public', 'host', '%s-cut.mp4' % stem)
    with open(os.path.join(wt, '%s-cut-wx.json' % stem)) as f:
        words = [w for w in json.load(f) if str(w.get('word', '')).strip()]
    if not words:
        sys.exit('verify_seams: no words in the cut transcript for %s' % stem)
    joins = join_times(os.path.join(wt, '%s-takes.json' % stem))
    reviewed = load_reviewed(os.path.join(wt, '%s-seams-reviewed.json' % stem))
    fails, warns, notes = [], [], []

    first = words[0]['start']
    if first > HEAD_MAX:
        msg = 'HEAD: %.2fs before the first word (max %.2f)' % (first, HEAD_MAX)
        rev = next((r for r in reviewed if r['a'] <= 0.05 and r['b'] >= first), None)
        if rev:
            notes.append('reviewed %s: %s' % (msg, rev['why']))
        else:
            fails.append(msg)

    gaps_checked = 0
    for w1, w2 in zip(words, words[1:]):
        gap = w2['start'] - w1['end']
        if gap < MIN_GAP:
            continue
        gaps_checked += 1
        rev = next((r for r in reviewed if r['a'] <= w1['end'] and w2['start'] <= r['b']), None)
        at_join = _join_inside(joins, w1['end'], w2['start'])
        word = w1['word'].strip()
        if gap > MAX_GAP:
            body = '%.2fs after "%s" (%.2fs, %s)' % (gap, word, w1['end'], 'at a cut join' if at_join else 'natural pause')
            if rev:
                notes.append('reviewed pause %s: %s' % (body, rev['why']))
            elif at_join:
                fails.append('DEAD AIR: ' + body)
            else:
                warns.append('LONG PAUSE: %s (kept: never cut in a natural pause)' % body)
        p = peak_db(cut, w1['end'] + EDGE_AFTER, w2['start'] - EDGE_BEFORE)
        if p > JUNK_DB:
            if rev:
                notes.append('reviewed sound %.1f dB after "%s": %s' % (p, word, rev['why']))
            elif at_join:
                fails.append('JUNK: %.1f dB sound in the %.2fs pause after "%s" (%.2fs) at a cut join' % (p, gap, word, w1['end']))
            else:
                notes.append('breath: %.1f dB in the natural pause after "%s" (%.2fs)' % (p, word, w1['end']))

    dur = duration_of(cut)
    last = words[-1]
    tail = dur - last['end']
    if tail > TAIL_MAX:
        msg = 'TAIL: %.2fs after the last word "%s" (max %.2f)' % (tail, last['word'].strip(), TAIL_MAX)
        rev = next((r for r in reviewed if r['a'] <= last['end'] and r['b'] >= dur - 0.05), None)
        if rev:
            notes.append('reviewed %s: %s' % (msg, rev['why']))
        else:
            fails.append(msg)

    out_dir = os.path.join(ROOT, 'qa', name)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'seams.json'), 'w') as f:
        json.dump({'cut': cut, 'gaps_checked': gaps_checked, 'head': round(first, 3), 'tail': round(tail, 3),
                   'fails': fails, 'warnings': warns, 'reviewed': notes}, f, indent=1)
    print('seams %s: %d pauses checked, head %.2fs, tail %.2fs, %d fail, %d warn'
          % (name, gaps_checked, first, tail, len(fails), len(warns)))
    for m in fails:
        print('  FAIL ' + m)
    for m in warns:
        print('  warn ' + m)
    for m in notes:
        print('  note ' + m)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
