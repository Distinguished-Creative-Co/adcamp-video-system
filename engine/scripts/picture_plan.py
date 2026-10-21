#!/usr/bin/env python3
"""Where the picture cuts, separately from where the sound cuts.

Two jobs, both run by last_take.py every time it renders the cut:

1. Source cuts (clips already edited in CapCut or Edits). A recording that was trimmed before it
   reached us has hard picture cuts in its pauses. If one of our boundaries lands a few frames from
   such a cut, a sliver of the other shot flashes on screen. snap_to_source_cuts() moves a boundary
   onto the source cut when one sits within SNAP of it on the kept side, provided the new boundary
   is still inside a silence (the HARD RULE never bends).

2. J-cuts. At every join the next sentence's voice starts a beat before its picture: the outgoing
   shot holds for LEAD seconds of its own trailing pause while the new voice begins, then the
   picture cuts. picture_spans() gives each kept segment a picture range [s + lead_in, e + lead_out]
   of the same total length as the sound, so timing, captions and checks downstream are unchanged.
   A lead only uses frames from the outgoing shot's own pause, never crosses a source cut, and
   falls to zero where the pause is too short.

    python3 scripts/picture_plan.py <input.mp4>     print the source cuts found (cached)
"""
import json
import math
import os
import re
import subprocess
import sys

FPS = 30
SCENE = 0.32          # scene-change score that counts as a hard cut in the source
SNAP = 0.30           # seconds: a source cut this close to a boundary pulls the boundary onto it
LEAD = 0.20           # seconds the next voice leads its picture at a join (6 frames)
MIN_LEAD = 2 / FPS    # below this a lead is dropped
MARGIN = 0.03         # stay this far inside a pause when borrowing its frames


def source_cuts(src):
    """Hard picture cuts already in the recording, in seconds. Cached next to the input."""
    cache = os.path.splitext(src)[0] + '.cuts.json'
    stamp = '%d:%d' % (os.path.getsize(src), int(os.path.getmtime(src)))
    if os.path.exists(cache):
        c = json.load(open(cache))
        if c.get('stamp') == stamp:
            return c['cuts']
    out = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', src, '-an', '-vf',
                          "scale=160:-2,select='gt(scene,%.2f)',showinfo" % SCENE, '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    cuts = sorted(round(float(m), 3) for m in re.findall(r'pts_time:([\d.]+)', out))
    json.dump({'stamp': stamp, 'cuts': cuts, 'threshold': SCENE}, open(cache, 'w'))
    return cuts


def _silence_at(t, S, min_len):
    return next(((s, e) for s, e in S if s - 0.006 <= t <= e + 0.006 and e - s >= min_len), None)


def snap_to_source_cuts(keep, S, cuts, min_join, duration):
    """Move boundaries onto nearby source cuts. Returns (new keep, notes)."""
    keep = [list(k) for k in keep]
    notes = []
    frame = 1 / FPS
    for i, (s, e) in enumerate(keep):
        if i > 0 or s > 0.05:          # a start that is a cut: a source cut just after it, inside the segment
            near = [c for c in cuts if s < c <= s + SNAP and c < e]
            if near:
                ns = round(near[-1] + frame / 2, 3)
                if _silence_at(ns, S, min_join):
                    notes.append('seg %d start %.3f -> %.3f (source cut at %.3f)' % (i, s, ns, near[-1]))
                    keep[i][0] = ns
                else:
                    notes.append('seg %d start %.3f: source cut at %.3f is in speech, left as is' % (i, s, near[-1]))
        if i < len(keep) - 1 or e < duration - 0.05:
            near = [c for c in cuts if e - SNAP <= c < e and c > keep[i][0]]
            if near:
                ne = round(near[0] - frame / 2, 3)
                if _silence_at(ne, S, min_join):
                    notes.append('seg %d end %.3f -> %.3f (source cut at %.3f)' % (i, e, ne, near[0]))
                    keep[i][1] = ne
                else:
                    notes.append('seg %d end %.3f: source cut at %.3f is in speech, left as is' % (i, e, near[0]))
    return [tuple(k) for k in keep], notes


def leads(keep, S, cuts, lead=LEAD):
    """The picture lead at every join (len(keep) - 1 values, seconds, whole frames)."""
    out = []
    for i in range(1, len(keep)):
        a_end = keep[i - 1][1]
        b_s, b_e = keep[i]
        pause = _silence_at(a_end, S, 0.0)
        room = (pause[1] - a_end - MARGIN) if pause else 0.0          # the outgoing shot's own pause
        nxt = [c for c in cuts if c > a_end]
        if nxt:
            room = min(room, nxt[0] - a_end - 1 / FPS)                  # never show the next source shot
        room = min(room, (b_e - b_s) - 0.3)                            # the incoming shot keeps most of itself
        val = math.floor(min(lead, room) * FPS + 1e-6) / FPS
        out.append(round(val, 4) if val >= MIN_LEAD else 0.0)
    return out


def picture_spans(keep, lead_list):
    spans = []
    for i, (s, e) in enumerate(keep):
        lin = lead_list[i - 1] if i > 0 else 0.0
        lout = lead_list[i] if i < len(keep) - 1 else 0.0
        spans.append((round(s + lin, 4), round(e + lout, 4)))
    return spans


def video_joins(keep, lead_list):
    """Cut-time seconds where the PICTURE changes (each sound join plus its lead)."""
    out, acc = [], 0.0
    for i, (s, e) in enumerate(keep[:-1]):
        acc += e - s
        out.append(round(acc + lead_list[i], 4))
    return out


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    c = source_cuts(sys.argv[1])
    print('%d source cuts: %s' % (len(c), ', '.join('%.2f' % x for x in c[:40])))
