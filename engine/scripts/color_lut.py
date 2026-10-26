#!/usr/bin/env python3
"""A video's color look: grades the host footage with one of AVS's LUTs (luts/<key>.cube), so the person's picture
takes the look while captions and graphics, drawn on top, keep the exact brand color.

    python3 scripts/color_lut.py <name>          after the cut exists; make_reel.sh runs it before the cutouts

The config's "color" names the look ("natural" or missing: nothing to do). Writes public/host/<stem>-cut-c.mp4 from the
cut (picture graded, sound copied untouched) and, when the full-resolution twin exists, <stem>-cut-hi-c.mp4. The
renderer draws the graded file when it's there (src/methodology/Root.tsx), and the cutouts and the render checks read
it too (reel_config.host_file). Reused while the cut and the look are unchanged.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import reel_config  # noqa: E402

LUTS = os.path.join(ROOT, 'luts')


def looks():
    return json.load(open(os.path.join(LUTS, 'luts.json')))


def grade(src, dst, lut):
    stamp = dst + '.json'
    want = {'lut': lut, 'src_size': os.path.getsize(src), 'src_mtime': int(os.path.getmtime(src))}
    if os.path.exists(dst) and os.path.exists(stamp) and json.load(open(stamp)) == want:
        return False
    tmp = dst + '.part.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-map', '0:v:0', '-map', '0:a?', '-vf',
                    'lut3d=%s:interp=tetrahedral' % os.path.join(LUTS, lut + '.cube'), '-c:v', 'libx264', '-crf', '16',
                    '-preset', 'medium', '-pix_fmt', 'yuv420p', '-c:a', 'copy', '-movflags', '+faststart', tmp], check=True)
    os.replace(tmp, dst)
    json.dump(want, open(stamp, 'w'))
    return True


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    name = sys.argv[1]
    cfg = reel_config.load(name)
    lut = cfg.get('color') or 'natural'
    cut = os.path.join(ROOT, 'public', cfg['src'])
    stem = cut[:-len('-cut.mp4')]
    outs = [(cut, stem + '-cut-c.mp4'), (stem + '-cut-hi.mp4', stem + '-cut-hi-c.mp4')]
    if lut == 'natural':
        for _, dst in outs:   # back to the footage as shot: the graded copies step aside
            for f in (dst, dst + '.json'):
                if os.path.exists(f):
                    os.remove(f)
        print('color: natural (the footage as shot)')
        return
    if lut not in {x['key'] for x in looks()}:
        sys.exit('color_lut: "%s" is not one of the color looks (%s)' % (lut, ', '.join(x['key'] for x in looks())))
    done = []
    for src, dst in outs:
        if os.path.exists(src):
            done.append(os.path.basename(dst) + (' (graded)' if grade(src, dst, lut) else ' (kept)'))
        elif os.path.exists(dst):
            os.remove(dst)   # a twin that no longer has its source never draws
    print('color: %s -> %s' % (lut, ', '.join(done) or 'no cut yet'))


if __name__ == '__main__':
    main()
