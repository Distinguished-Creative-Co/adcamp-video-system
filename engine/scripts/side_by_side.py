#!/usr/bin/env python3
"""Put an example reel's frames over frames of our render, to check a rebuilt style against what inspired it.

    "$AVS_MATTE_PYTHON" scripts/side_by_side.py <example file> <our video> [--n 8] [--out <file.jpg>]

Top row: the example at evenly spaced points through its length. Bottom row: our video at the same points
through ITS length (the words differ, so the moments line up by position, not by time). Look at type,
case, color, size against the frame, where the words sit, plates and the grade. Default output:
qa/side-by-side-<our video's name>.jpg
"""
import io
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def length(p):
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p],
                                capture_output=True, text=True).stdout.strip())


def grab(p, t):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', '%.3f' % t, '-i', p, '-frames:v', '1', '-vf', 'scale=300:534:force_original_aspect_ratio=decrease,pad=300:534:(ow-iw)/2:(oh-ih)/2',
                          '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True).stdout
    return Image.open(io.BytesIO(raw)).convert('RGB') if raw else Image.new('RGB', (300, 534))


def main():
    a = sys.argv[1:]
    pos = [x for i, x in enumerate(a) if not x.startswith('--') and (i == 0 or a[i - 1] not in ('--n', '--out'))]
    if len(pos) != 2:
        sys.exit(__doc__)
    ex, ours = pos
    n = int(a[a.index('--n') + 1]) if '--n' in a else 8
    out = a[a.index('--out') + 1] if '--out' in a else os.path.join(ROOT, 'qa', 'side-by-side-%s.jpg' % os.path.splitext(os.path.basename(ours))[0])
    le, lo = length(ex), length(ours)
    pad, top = 6, 34
    sheet = Image.new('RGB', (n * 300 + (n + 1) * pad, 2 * 534 + 3 * pad + 2 * top), (24, 24, 24))
    d = ImageDraw.Draw(sheet)
    try:
        f = ImageFont.load_default(size=22)
    except TypeError:
        f = ImageFont.load_default()
    d.text((pad, 6), 'EXAMPLE', font=f, fill=(255, 255, 0))
    d.text((pad, top + 534 + pad + 6), 'OURS', font=f, fill=(255, 255, 0))
    for i in range(n):
        u = (i + 0.5) / n
        x = pad + i * (300 + pad)
        sheet.paste(grab(ex, u * le), (x, top))
        sheet.paste(grab(ours, u * lo), (x, top + 534 + pad + top))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sheet.save(out, quality=88)
    print('side_by_side: %s' % out)


if __name__ == '__main__':
    main()
