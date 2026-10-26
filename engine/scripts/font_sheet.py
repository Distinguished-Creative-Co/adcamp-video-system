#!/usr/bin/env python3
"""The font pairs on one picture, set in the person's own name, to pick from by looking.

    python3 scripts/font_sheet.py ["Their Name"] [--accent "#RRGGBB"] [--out <file.png>]

Writes out/font-sheet.png (default). Put it in the chat and ask "Which one, 1 to 4?" The answer maps to
brand.json: 1 hanken + playfair, 2 inter + instrument, 3 montserrat + fraunces, 4 dmsans + dmserif.
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAIRS = {1: ('hanken', 'playfair'), 2: ('inter', 'instrument'), 3: ('montserrat', 'fraunces'), 4: ('dmsans', 'dmserif')}


def main():
    a = sys.argv[1:]
    flags = ('--accent', '--out')
    pos = [x for i, x in enumerate(a) if not x.startswith('--') and (i == 0 or a[i - 1] not in flags)]
    name = pos[0] if pos else ''
    try:
        accent = json.load(open(os.path.join(ROOT, 'src', 'brand.json'))).get('accent', '#F7C715')
    except (OSError, ValueError):
        accent = '#F7C715'
    accent = a[a.index('--accent') + 1] if '--accent' in a else accent
    out = os.path.abspath(a[a.index('--out') + 1]) if '--out' in a else os.path.join(ROOT, 'out', 'font-sheet.png')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    props = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False)
    json.dump({'name': name, 'accent': accent}, props)
    props.close()
    p = subprocess.run(['npx', 'remotion', 'still', 'src/methodology/index.ts', 'FontSheet', out, '--props=' + props.name, '--log=error'],
                       cwd=ROOT, capture_output=True, text=True)
    os.remove(props.name)
    if p.returncode != 0:
        sys.exit('font_sheet: render failed: ' + (p.stderr or p.stdout)[-400:])
    print('font_sheet: %s' % out)


if __name__ == '__main__':
    main()
