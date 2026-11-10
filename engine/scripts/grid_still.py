#!/usr/bin/env python3
"""A gridded still of a video, to find the face center (X,Y in 1080x1920) and see whether text in the shot reads
backwards. iPhone HDR footage gets the same tone-map as the build, so the still looks as the video will.

    python3 scripts/grid_still.py <video> <out.png> [--unmirror] [--at 3]

--unmirror flips it first, as the build does for mirrored front-camera footage (X then comes from the flipped picture).
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import normalize_source  # noqa: E402


def main():
    a = sys.argv[1:]
    pos = [x for i, x in enumerate(a) if not x.startswith('--') and (i == 0 or a[i - 1] != '--at')]
    if len(pos) != 2:
        sys.exit(__doc__)
    video, out = pos
    at = a[a.index('--at') + 1] if '--at' in a else '3'
    if not os.path.isfile(video):
        sys.exit('grid_still: no video at %s' % video)
    try:
        trc = next(x.get('color_transfer') for x in normalize_source.probe(video)['streams'] if x.get('codec_type') == 'video')
    except (subprocess.CalledProcessError, StopIteration, ValueError, KeyError):
        trc = None
    vf = normalize_source.tonemap_vf(trc) + ('hflip,' if '--unmirror' in a else '') + 'scale=1080:1920,drawgrid=w=108:h=192:t=2:c=red@0.6'
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    if subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', at, '-i', video, '-frames:v', '1', '-vf', vf, out]).returncode:
        sys.exit('grid_still: ffmpeg could not make the still from %s' % video)
    print('grid still: %s%s' % (out, ' (HDR tone-mapped)' if trc in ('arib-std-b67', 'smpte2084') else ''))


if __name__ == '__main__':
    if '--help' in sys.argv[1:] or sys.argv[1:2] == ['-h']:   # --help: the usage, nothing else
        print((__doc__ or '').strip() or 'usage: python3 scripts/%s' % os.path.basename(__file__))
        sys.exit(0)
    main()
