#!/usr/bin/env python3
"""Render the companion pack for a reel (adapted from Georgy): covers and static ads, built
from the reel's own config, so they carry only its approved title, stat and CTA.

    python3 scripts/companions.py <name>

Writes out/<name>-companions/{cover-vertical,cover-feed,static-square,static-feed,static-vertical}.png
(+ thumbnail.png when the config has a thumbnail: run matte_reel.py first)
and a review sheet. Each format is recomposed, never stretched. Inspect every PNG at phone
size and check Ads Manager placement previews before any of it runs as an ad.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORMATS = ['cover-vertical', 'cover-feed', 'static-square', 'static-feed', 'static-vertical']


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    name = sys.argv[1]
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import reel_config
    rc = reel_config.load(name)
    cover = rc.get('cover') or {}
    if not cover.get('title'):
        # a captions-only reel has no title or proof to put on a static: an empty card is filler
        print('companions: skipped (%s has no cover title, so there is nothing for a static ad to say)' % name)
        return
    out = os.path.join(ROOT, 'out', '%s-companions' % name)
    os.makedirs(out, exist_ok=True)
    bundle = os.path.join(ROOT, '.qa-bundle')
    subprocess.run(['npx', 'remotion', 'bundle', 'src/methodology/index.ts', '--out-dir', bundle, '--log=error'], cwd=ROOT, check=True)
    paths = []
    for fmt in FORMATS + (['thumbnail'] if rc.get('thumbnail') else []):
        p = os.path.join(out, '%s.png' % fmt)
        subprocess.run(['npx', 'remotion', 'still', bundle, '%s--%s' % (name, fmt), p, '--log=error'], cwd=ROOT, check=True, capture_output=True)
        paths.append(p)
    ins, fg = [], ''
    for i, p in enumerate(paths):
        ins += ['-i', p]
        fg += '[%d]scale=-1:640[s%d];' % (i, i)
    fg += ''.join('[s%d]' % i for i in range(len(paths))) + 'hstack=inputs=%d' % len(paths)
    subprocess.run(['ffmpeg', '-v', 'error', '-y'] + ins + ['-filter_complex', fg, os.path.join(out, 'sheet.png')], check=True)
    print('wrote %d companions + sheet.png to %s' % (len(paths), os.path.relpath(out, ROOT)))


if __name__ == '__main__':
    main()
