#!/usr/bin/env python3
"""Draw the DRAFT badge burned into review drafts, as a transparent PNG.

    python3 scripts/draft_badge.py <out.png> [width]

A draft is the edit at half size so the creator can judge it in motion before approving the real
render. The badge says it is not the one to post. Drawn with Pillow (both cutout environments have it)
so the draft never depends on an ffmpeg built with drawtext.
"""
import sys

from PIL import Image, ImageDraw, ImageFont


def main():
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    out = sys.argv[1]
    width = int(sys.argv[2]) if len(sys.argv) == 3 else 540
    scale = width / 540
    text = 'DRAFT  ·  not for posting'
    font = ImageFont.load_default(size=round(20 * scale))
    probe = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    x0, y0, x1, y1 = probe.textbbox((0, 0), text, font=font)
    pad_x, pad_y = round(16 * scale), round(9 * scale)
    w, h = x1 - x0 + 2 * pad_x, y1 - y0 + 2 * pad_y
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 2, fill=(200, 30, 30, 225))
    d.text((pad_x - x0, pad_y - y0), text, font=font, fill=(255, 255, 255, 255))
    img.save(out)


if __name__ == '__main__':
    main()
