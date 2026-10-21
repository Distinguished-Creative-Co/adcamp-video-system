#!/usr/bin/env python3
"""Silence-gated cutting: join chosen stretches of a recording, but only at real pauses.

    python3 scripts/hostcut.py <src> --keep "s:e,s:e,..." [--out cut.mp4] [--check-only]
        [--forbid "s:e,..."] [--noise-db -30] [--min-d 0.06] [--min-join-silence 0.15]
        [--tol 0.05] [--crf 18]

THE HARD RULE: every boundary of every keep segment must sit inside a detected silence of
at least `min_join_silence` seconds. The only exemptions are a first segment that starts at
the head of the file and a last segment that ends at its tail. render_cut() runs the check
before it encodes anything, so a cut through a word can never reach the output file.

Library use (last_take.py, hostcut_plan.py): probe_duration, detect_silences,
detect_reset_spans, assert_cuts_in_silence, render_cut and the three exception classes.
Python 3.9 compatible, standard library plus ffmpeg/ffprobe on PATH.
"""
import argparse
import re
import subprocess
import sys

MAX_TOL = 0.08           # ceiling on the head/tail exemption tolerance (seconds)
DEFAULT_MIN_JOIN = 0.15  # shortest pause a boundary may sit in (seconds)
EPS = 0.006              # float slack for "is this time inside that silence"


class MidWordRejoinError(Exception):
    """A keep boundary does not sit inside a long-enough silence."""


class ForbiddenSpanError(Exception):
    """A kept segment overlaps a span that must not appear in the cut."""


class CutSpecError(Exception):
    """The keep list itself is malformed."""


# ── measuring the file ──────────────────────────────────────────────────────────────────
def probe_duration(src):
    """Container duration of a media file, in seconds."""
    res = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                          '-of', 'default=noprint_wrappers=1:nokey=1', src],
                         capture_output=True, text=True, check=True)
    return float(res.stdout.strip().splitlines()[0])


def merge_intervals(intervals, gap=1e-6):
    """Sorted union of (start, end) pairs; pairs closer than `gap` fuse into one."""
    merged = []
    for s, e in sorted((float(a), float(b)) for a, b in intervals):
        if e <= s:
            continue
        if merged and s <= merged[-1][1] + gap:
            if e > merged[-1][1]:
                merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    return merged


_SD_EVENT = re.compile(r'silence_(start|end):\s*(-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)')


def parse_silencedetect(stderr, duration, min_d=0.0):
    """Turn ffmpeg silencedetect log text into merged (start, end) intervals."""
    found = []
    opened = None
    for kind, value in _SD_EVENT.findall(stderr):
        t = max(float(value), 0.0)
        if kind == 'start':
            if opened is not None and t > opened:
                found.append((opened, t))
            opened = t
        else:
            if opened is not None and t > opened:
                found.append((opened, t))
            opened = None
    if opened is not None:
        if duration is not None and duration > opened:
            found.append((opened, float(duration)))
        else:
            end = opened + max(min_d, 0.001)
            sys.stderr.write('hostcut: silence open at %.3fs runs past the duration (%s), closed at %.3fs\n'
                             % (opened, duration, end))
            found.append((opened, end))
    return merge_intervals(found)


def _silencedetect_pass(src, noise_db, min_d, duration):
    cmd = ['ffmpeg', '-hide_banner', '-nostats', '-i', src,
           '-af', 'silencedetect=noise=%sdB:d=%s' % (noise_db, min_d), '-f', 'null', '-']
    res = subprocess.run(cmd, capture_output=True, text=True)
    return parse_silencedetect(res.stderr, duration, min_d=min_d)


def _intersect(a, b):
    """Times that are silent in both interval lists (both sorted and merged)."""
    out = []
    i = j = 0
    while i < len(a) and j < len(b):
        lo = max(a[i][0], b[j][0])
        hi = min(a[i][1], b[j][1])
        if hi > lo:
            out.append((lo, hi))
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return out


def detect_silences(src, noise_db=-30.0, min_d=0.06, duration=None, strict_db=-40.0):
    """Silences of `src`. With `strict_db`, a time is silent only if a second, stricter pass
    agrees, and slivers split by under 5 ms of disagreement are rejoined."""
    if duration is None:
        duration = probe_duration(src)
    loose = _silencedetect_pass(src, noise_db, min_d, duration)
    if strict_db is None:
        return loose
    strict = _silencedetect_pass(src, strict_db, min_d, duration)
    return merge_intervals(_intersect(loose, strict), gap=0.005)


# ── spoken "reset, reset" cues ──────────────────────────────────────────────────────────
def _letters(word):
    return re.sub(r'[^a-z]', '', word.lower())


def _cue_groups(words, toks, min_repeat, max_gap):
    groups = []
    i, n = 0, len(toks)
    while i < n:
        if toks[i] != 'reset':
            i += 1
            continue
        j = i
        while j + 1 < n and toks[j + 1] == 'reset' and words[j + 1]['start'] - words[j]['end'] <= max_gap:
            j += 1
        if j - i + 1 >= min_repeat:
            groups.append((i, j))
        i = j + 1
    return groups


def _ends_sentence(raw):
    return raw.strip()[-1:] in ('.', '?', '!')


def _clamp(v, lo, hi):
    """Clamp v to lo first, then cap at hi (hi wins if the window is inverted)."""
    return min(hi, max(lo, v))


def _widen(a, b, pad):
    return a - pad, b + pad


def _flub_start(words, toks, gi, gj, prev_cue_idx):
    """Index of the first word of the take the cue throws away."""
    after = toks[gj + 1:gj + 9]
    for skip in range(3):
        tri = [t for t in after[skip:skip + 3] if t]
        if len(tri) < 3:
            break
        hits = [i for i in range(prev_cue_idx + 1, gi - 2) if toks[i:i + 3] == tri]
        if hits:
            return hits[-1]
    # no echo found: the flub began right after the last finished sentence before the cue
    stop = gi - 1
    for stop in range(gi - 1, prev_cue_idx - 1, -1):
        if stop == prev_cue_idx or _ends_sentence(words[stop]['word']):
            break
    return min(stop + 1, gi)


def detect_reset_spans(words, silences, *, min_repeat=2, max_gap=1.2, min_join_silence=DEFAULT_MIN_JOIN):
    """One record per spoken cue group: the stretch to cut (pause before the flubbed take to
    the pause after the cue) and the span that must never survive into the cut."""
    sil = merge_intervals(silences)
    toks = [_letters(w['word']) for w in words]
    n = len(words)

    def mid_of_silence(lo, hi):
        best = None
        for gap in sil:
            span = gap[1] - gap[0]
            touches = gap[0] < hi + 1e-6 and gap[1] > lo - 1e-6
            if touches and span >= min_join_silence - 1e-9 and (best is None or span > best[1] - best[0]):
                best = gap
        if best is None:
            return None
        g0, g1 = best
        centre = 0.5 * (max(g0, lo) + min(g1, hi))
        return _clamp(centre, g0 + 0.02, g1 - 0.02)

    out = []
    prev_cue_idx = -1
    for gi, gj in _cue_groups(words, toks, min_repeat, max_gap):
        fi = _flub_start(words, toks, gi, gj, prev_cue_idx)
        fs = words[fi]['start']
        cue_end = words[gj]['end']
        prev_end = words[fi - 1]['end'] if fi > 0 else 0.0
        nxt = words[gj + 1]['start'] if gj + 1 < n else cue_end + 5.0
        pad = 0.05
        cs = mid_of_silence(*_widen(prev_end, fs, pad))      # the pause before the flubbed take
        ce = mid_of_silence(*_widen(cue_end, nxt, pad))      # the pause after the cue words
        if ce is None:
            ce = mid_of_silence(cue_end - 0.10, cue_end + 4.0)   # word times drift after a flub
        ok = cs is not None and ce is not None and ce > cs
        out.append({'cut': (cs, ce) if ok else None,
                    'forbid': (max(fs - 0.01, 0.0), cue_end + 0.01),
                    'ok': ok, 'flub_start': fs, 'cue_end': cue_end,
                    'b': words[fi - 1]['word'] if fi > 0 else '[start]',
                    'a': words[gj + 1]['word'] if gj + 1 < n else '[end]'})
        prev_cue_idx = gj
    return out


# ── the rule ────────────────────────────────────────────────────────────────────────────
def validate_keep_segments(keep, duration):
    if not keep:
        raise CutSpecError('keep list is empty')
    prev_end = None
    for i, seg in enumerate(keep):
        if not isinstance(seg, (list, tuple)) or len(seg) != 2:
            raise CutSpecError('segment %d is not a (start, end) pair: %r' % (i, seg))
        s, e = float(seg[0]), float(seg[1])
        if e <= s:
            raise CutSpecError('segment %d ends at or before its start (%.3f-%.3f)' % (i, s, e))
        if s < -1e-6:
            raise CutSpecError('segment %d starts before 0 (%.3f)' % (i, s))
        if e > duration + 1e-3:
            raise CutSpecError('segment %d ends at %.3f, past the %.3fs source' % (i, e, duration))
        if prev_end is not None and s < prev_end - 1e-6:
            raise CutSpecError('segment %d starts at %.3f, before segment %d ends (%.3f)' % (i, s, i - 1, prev_end))
        prev_end = e


def assert_cuts_in_silence(keep, silences, duration, *, tol=0.05, min_join_silence=DEFAULT_MIN_JOIN,
                           forbidden_spans=None):
    """Raise unless every boundary of `keep` lands inside a real pause. Returns True."""
    tol = min(max(float(tol), 0.0), MAX_TOL)
    validate_keep_segments(keep, duration)
    segs = [(float(s), float(e)) for s, e in keep]
    sil = merge_intervals(silences)

    if forbidden_spans:
        clashes = []
        for i, (s, e) in enumerate(segs):
            for fa, fb in forbidden_spans:
                if s < fb - 1e-9 and e > fa + 1e-9:
                    clashes.append('seg%d (%.3f-%.3f) overlaps forbidden %.3f-%.3f' % (i, s, e, fa, fb))
        if clashes:
            raise ForbiddenSpanError('kept audio overlaps a forbidden span: ' + '; '.join(clashes))

    usable = [(s, e) for s, e in sil if e - s >= min_join_silence - 1e-9]

    def in_pause(t):
        return any(s - EPS <= t <= e + EPS for s, e in usable)

    bad = []
    last = len(segs) - 1
    for i, (s, e) in enumerate(segs):
        if not (i == 0 and s <= tol) and not in_pause(s):
            bad.append('seg%d.start=%.3fs' % (i, s))
        if not (i == last and e >= duration - tol) and not in_pause(e):
            bad.append('seg%d.end=%.3fs' % (i, e))
    if bad:
        raise MidWordRejoinError(
            'HARD RULE violation: these boundaries are not inside a silence of at least %.2fs: %s. '
            'Re-cut so every boundary lands in a real pause.' % (min_join_silence, ', '.join(bad)))
    return True


# ── rendering ───────────────────────────────────────────────────────────────────────────
def _filter_graph(keep):
    parts, pads = [], []
    for i, (s, e) in enumerate(keep):
        parts.append('[0:v]trim=%.3f:%.3f,setpts=PTS-STARTPTS[v%d]' % (s, e, i))
        parts.append('[0:a]atrim=%.3f:%.3f,asetpts=PTS-STARTPTS[a%d]' % (s, e, i))
        pads.append('[v%d][a%d]' % (i, i))
    parts.append('%sconcat=n=%d:v=1:a=1[outv][outa]' % (''.join(pads), len(keep)))
    return ';'.join(parts)


def _split_graph(segs, pics):
    """Picture and sound joined separately (their joins may sit apart: J-cuts), each one concat."""
    parts = []
    for i, (s, e) in enumerate(pics):
        parts.append('[0:v]trim=%.3f:%.3f,setpts=PTS-STARTPTS[v%d]' % (s, e, i))
    for i, (s, e) in enumerate(segs):
        parts.append('[0:a]atrim=%.3f:%.3f,asetpts=PTS-STARTPTS[a%d]' % (s, e, i))
    parts.append('%sconcat=n=%d:v=1:a=0[outv]' % (''.join('[v%d]' % i for i in range(len(pics))), len(pics)))
    parts.append('%sconcat=n=%d:v=0:a=1[outa]' % (''.join('[a%d]' % i for i in range(len(segs))), len(segs)))
    return ';'.join(parts)


def render_cut(src, keep, out, *, noise_db=-30.0, min_d=0.06, tol=0.05, min_join_silence=DEFAULT_MIN_JOIN,
               forbidden_spans=None, silences=None, duration=None, crf=18, preset='medium', picture=None):
    """Check `keep` against the silence map, then encode the joined segments to `out`.
    picture: optional picture ranges, one per keep segment, of the same total length (J-cuts:
    scripts/picture_plan.py). The sound always follows `keep`; the gate always checks `keep`."""
    if duration is None:
        duration = probe_duration(src)
    if silences is None:
        silences = detect_silences(src, noise_db=noise_db, min_d=min_d, duration=duration)
    assert_cuts_in_silence(keep, silences, duration, tol=tol, min_join_silence=min_join_silence,
                           forbidden_spans=forbidden_spans)
    segs = [(float(s), float(e)) for s, e in keep]
    graph = _filter_graph(segs)
    if picture is not None:
        pics = [(float(s), float(e)) for s, e in picture]
        if len(pics) != len(segs) or abs(sum(e - s for s, e in pics) - sum(e - s for s, e in segs)) > 0.002 \
                or any(s < -1e-6 or e > duration + 1e-3 or e <= s for s, e in pics):
            raise CutSpecError('picture spans must match the keep list in count and total length, inside the source')
        graph = _split_graph(segs, pics)
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-i', src, '-filter_complex', graph,
           '-map', '[outv]', '-map', '[outa]',
           '-c:v', 'libx264', '-crf', str(crf), '-preset', preset, '-pix_fmt', 'yuv420p',
           '-c:a', 'aac', '-b:a', '192k', out]
    subprocess.run(cmd, check=True)
    return out


# ── command line ────────────────────────────────────────────────────────────────────────
def _pairs(text):
    out = []
    for item in text.split(','):
        item = item.strip()
        if not item:
            continue
        a, b = item.split(':')
        out.append((float(a), float(b)))
    return out


def main():
    ap = argparse.ArgumentParser(description='Join keep segments, only at real pauses.')
    ap.add_argument('src')
    ap.add_argument('--keep', required=True, help='"s:e,s:e,..." in source seconds')
    ap.add_argument('--out')
    ap.add_argument('--check-only', action='store_true')
    ap.add_argument('--forbid', default='', help='"s:e,..." spans that must not be kept')
    ap.add_argument('--noise-db', type=float, default=-30.0)
    ap.add_argument('--min-d', type=float, default=0.06)
    ap.add_argument('--min-join-silence', type=float, default=DEFAULT_MIN_JOIN)
    ap.add_argument('--tol', type=float, default=0.05)
    ap.add_argument('--crf', type=int, default=18)
    a = ap.parse_args()

    if a.tol > MAX_TOL:
        sys.stderr.write('hostcut: --tol %.3f is above the %.2fs ceiling, %.2fs is used\n' % (a.tol, MAX_TOL, MAX_TOL))
    try:
        keep = _pairs(a.keep)
        forbid = _pairs(a.forbid) or None
    except ValueError as ex:
        sys.exit('REJECTED: could not parse a span list (%s)' % ex)
    dur = probe_duration(a.src)
    sil = detect_silences(a.src, noise_db=a.noise_db, min_d=a.min_d, duration=dur)
    try:
        assert_cuts_in_silence(keep, sil, dur, tol=a.tol, min_join_silence=a.min_join_silence, forbidden_spans=forbid)
    except (MidWordRejoinError, ForbiddenSpanError, CutSpecError) as ex:
        sys.exit('REJECTED: %s' % ex)
    print('OK: %d segments, all boundaries land in silence (>= %.2fs).' % (len(keep), a.min_join_silence))
    if a.check_only:
        return
    if not a.out:
        sys.exit('error: --out is required to render (or pass --check-only)')
    render_cut(a.src, keep, a.out, tol=a.tol, min_join_silence=a.min_join_silence, forbidden_spans=forbid,
               silences=sil, duration=dur, crf=a.crf)
    print('wrote %s' % a.out)


if __name__ == '__main__':
    main()
