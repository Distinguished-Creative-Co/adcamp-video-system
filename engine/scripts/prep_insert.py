#!/usr/bin/env python3
"""Prepare one of the person's own clips as a cutaway insert.

    python3 scripts/prep_insert.py <clip.mov|mp4> <name> [--start S] [--length L]

Writes public/inserts/<name>.mp4: muted, 30 fps, h264, cropped to 16:9 at 1520x856 (twice
the card size, so it stays sharp), rotation from the phone applied. --start skips S seconds
of the clip, --length keeps L seconds (default: up to 20). Then in the reel's config:

    "inserts": [{"kind": "clip", "in": 345, "out": 395, "src": "inserts/<name>.mp4", "label": "Our Midtown office"}]

Only the person's own footage goes here. Never stock, never someone else's video.
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
W, H, FPS, MAX_LEN = 1520, 856, 30, 20.0


def main():
    flags = {i for i, a in enumerate(sys.argv) if a in ('--start', '--length')}
    args = [a for i, a in enumerate(sys.argv) if i and i not in flags and i - 1 not in flags]
    if len(args) != 2:
        sys.exit(__doc__)
    src, name = args
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', name):
        sys.exit('prep_insert: the name is kebab-case letters, digits and dashes (e.g. office-walkthrough)')
    start = float(sys.argv[sys.argv.index('--start') + 1]) if '--start' in sys.argv else 0.0
    length = float(sys.argv[sys.argv.index('--length') + 1]) if '--length' in sys.argv else MAX_LEN
    if not os.path.exists(src):
        sys.exit('prep_insert: no such file: %s' % src)
    out = os.path.join(ROOT, 'public', 'inserts', '%s.mp4' % name)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-ss', '%.3f' % start, '-t', '%.3f' % length, '-i', src, '-an',
           '-vf', 'scale=%d:%d:force_original_aspect_ratio=increase:flags=lanczos,crop=%d:%d' % (W, H, W, H),
           '-r', str(FPS), '-fps_mode', 'cfr', '-c:v', 'libx264', '-crf', '20', '-preset', 'medium', '-pix_fmt', 'yuv420p',
           '-movflags', '+faststart', out]
    subprocess.run(cmd, check=True)
    info = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-print_format', 'json', '-show_format', out],
                                     capture_output=True, text=True).stdout)
    dur = float(info['format']['duration'])
    print('prep_insert: wrote %s (%.1fs, %dx%d, muted). Fits an insert of up to %d frames.' % (os.path.relpath(out, ROOT), dur, W, H, int(dur * FPS)))


if __name__ == '__main__':
    main()
