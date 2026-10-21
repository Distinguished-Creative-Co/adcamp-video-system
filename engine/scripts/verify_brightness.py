#!/usr/bin/env python3
"""Flash scan on a finished video: one-frame white spikes and hard brightening jumps.

    python3 scripts/verify_brightness.py <mp4> [--fps 30] [--spike 30] [--jump 90]

Average luma (YAVG, 0-255) is read per frame from a small downscale. A SPIKE is a frame at
least --spike brighter than both neighbours; a BRIGHT JUMP is a rise of at least --jump from
the previous frame. Both fail. A DARK CUT (a drop of --jump or more) is listed for
information only: a hard cut into a dark scene is a choice, not a flash.
Exit 0 on PASS, 1 on FAIL or when no frames could be read.
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile


def luma_per_frame(mp4):
    fd, tmp = tempfile.mkstemp(prefix='luma-', suffix='.txt')
    os.close(fd)
    try:
        subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-i', mp4,
                        '-vf', 'scale=128:72,signalstats,metadata=mode=print:file=%s' % tmp,
                        '-an', '-f', 'null', '-'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        rows, frame = [], None
        with open(tmp) as f:
            for line in f:
                m = re.search(r'frame:\s*(\d+)', line)
                if m:
                    frame = int(m.group(1))
                    continue
                m = re.search(r'YAVG=([-\d.]+)', line)
                if m and frame is not None:
                    rows.append((frame, float(m.group(1))))
                    frame = None
        return rows
    finally:
        os.remove(tmp)


def main():
    ap = argparse.ArgumentParser(description='Scan a render for flashes.')
    ap.add_argument('mp4')
    ap.add_argument('--fps', type=float, default=30.0)
    ap.add_argument('--spike', type=float, default=30.0)
    ap.add_argument('--jump', type=float, default=90.0)
    a = ap.parse_args()

    rows = luma_per_frame(a.mp4)
    if not rows:
        print('no frames read from %s' % a.mp4)
        return 1
    spikes, jumps, darks = [], [], []
    for k in range(1, len(rows)):
        f, y = rows[k]
        prev = rows[k - 1][1]
        if k + 1 < len(rows):
            nxt = rows[k + 1][1]
            if y - prev >= a.spike and y - nxt >= a.spike:
                spikes.append((f, prev, y, nxt))
        if y - prev >= a.jump:
            jumps.append((f, prev, y))
        if y - prev <= -a.jump:
            darks.append((f, prev, y))

    print('scanned %d frames from %s' % (len(rows), a.mp4))
    for f, prev, y in darks:
        print('  info DARK CUT frame %d (%.2fs): luma %.1f -> %.1f (a hard cut into a dark scene)' % (f, f / a.fps, prev, y))
    if not spikes and not jumps:
        print('PASS: no one-frame spikes (>= %g) and no bright jumps (>= %g)' % (a.spike, a.jump))
        return 0
    print('FAIL: %d spike(s), %d bright jump(s)' % (len(spikes), len(jumps)))
    for f, prev, y, nxt in spikes:
        print('  SPIKE frame %d (%.2fs): luma %.1f -> %.1f -> %.1f' % (f, f / a.fps, prev, y, nxt))
    for f, prev, y in jumps:
        print('  BRIGHT JUMP frame %d (%.2fs): luma %.1f -> %.1f' % (f, f / a.fps, prev, y))
    return 1


if __name__ == '__main__':
    sys.exit(main())
