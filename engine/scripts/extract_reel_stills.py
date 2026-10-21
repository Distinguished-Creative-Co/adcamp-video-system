#!/usr/bin/env python3
"""Stills at every state change + a contact sheet, for EYES-ON review of rendered frames.

    python3 scripts/extract_reel_stills.py <name> out/<name>.mp4   stills from the finished render
    python3 scripts/extract_reel_stills.py <name> --preview       engine stills BEFORE render (Remotion still,
                                                                   for reviewing the scene map; not the deliverable)

Frames: the open, the open settled, each scene change (just before, mid-glide, settled),
each swap (mid-in, settled, mid-out, returned), and one every 2s. Writes
qa/<name>/stills/fNNNN.png (or qa/<name>/preview/) and sheet.png.
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import reel_config  # noqa: E402

GLIDE_F, SWAP_F = 20, 18


def key_frames(cfg):
    n = cfg['frames']
    fs = {0, cfg['open']['frames'] // 2, cfg['open']['frames'] + 2}
    for sc in cfg['scenes'][1:]:
        fs |= {sc['from'] - 2, sc['from'] + GLIDE_F // 2, sc['from'] + GLIDE_F + 10}
    for s in cfg['swaps']:
        fs |= {s['in'] + SWAP_F // 2, s['in'] + SWAP_F + 12}
        if s['out'] < n:
            fs |= {s['out'] + SWAP_F // 2, s['out'] + SWAP_F + 10}
    fs |= set(range(60, n, 60))
    fs.add(n - 3)
    return sorted(f for f in fs if 0 <= f < n)


def sheet(paths, out, cols=6):
    tiles = []
    for p in paths:
        tiles += ['-i', p]
    rows = (len(paths) + cols - 1) // cols
    pad = rows * cols - len(paths)
    fg = ''.join('[%d]scale=270:480,drawtext=text=%s:x=8:y=8:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.6[t%d];'
                 % (i, os.path.basename(p)[1:-4], i) for i, p in enumerate(paths))
    labels = ''.join('[t%d]' % i for i in range(len(paths)))
    if pad:
        fg += ''.join('color=c=black:s=270x480:d=1[p%d];' % i for i in range(pad))
        labels += ''.join('[p%d]' % i for i in range(pad))
    fg += '%sxstack=inputs=%d:layout=%s[out]' % (labels, rows * cols, '|'.join(
        '%d_%d' % (c * 270, r * 480) for r in range(rows) for c in range(cols)))
    subprocess.run(['ffmpeg', '-v', 'error', '-y'] + tiles + ['-filter_complex', fg, '-map', '[out]', '-frames:v', '1', out], check=True)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    name, target = sys.argv[1], sys.argv[2]
    cfg = reel_config.load(name)
    frames = key_frames(cfg)
    preview = target == '--preview'
    d = os.path.join(ROOT, 'qa', name, 'preview' if preview else 'stills')
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    paths = []
    if preview:
        bundle = os.path.join(ROOT, '.qa-bundle')
        subprocess.run(['npx', 'remotion', 'bundle', 'src/methodology/index.ts', '--out-dir', bundle, '--log=error'],
                       cwd=ROOT, check=True)
        for f in frames:
            p = os.path.join(d, 'f%04d.png' % f)
            subprocess.run(['npx', 'remotion', 'still', bundle, name, p, '--frame=%d' % f, '--log=error'],
                           cwd=ROOT, check=True, capture_output=True)
            paths.append(p)
    else:
        for f in frames:
            p = os.path.join(d, 'f%04d.png' % f)
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', '%.4f' % (f / 30.0), '-i', target,
                            '-frames:v', '1', p], check=True)
            paths.append(p)
    sheet(paths, os.path.join(d, 'sheet.png'))
    print('wrote %d stills + sheet.png to %s' % (len(paths), os.path.relpath(d, ROOT)))


if __name__ == '__main__':
    main()
