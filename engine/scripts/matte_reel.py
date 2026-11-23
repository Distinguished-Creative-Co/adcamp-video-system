#!/usr/bin/env python3
"""Foreground cutouts for BACK TEXT (big highlighted words that sit behind the host) and LIGHTS DOWN.

    "$AVS_MATTE_PYTHON" scripts/matte_reel.py <name>

For every entry in the config's "backText", cuts the host out of the cut over that entry's
frames with MediaPipe's selfie segmenter (Apache-2.0, runs locally) and writes
public/host/<stem>-fg-<in>-<out>.webm: the same pixels as the cut, with an alpha channel that
keeps only the person. The engine draws  footage -> back text -> this cutout,  so the words
read as standing in the room behind the host. A lights-down effect dims the room behind the
host, so its cutout (<stem>-fg-ld-<in>-<out>.webm) has its edge pulled in and feathered: against a
dark room a soft edge that carries the bright background would show as a halo. The thumbnail
cutout, and a cover with words behind the host, is one frame, written as a PNG. Only the listed frames are processed. Cutouts are reused while the cut and the range are
unchanged.

The segmenter runs twice per frame: once on the full frame to find the person, once on a
crop around them (four times the detail per pixel). A guided filter then pulls the mask edge
onto the real edges in the picture, and a light temporal blend keeps it steady between frames. Then clean() fixes two
small misses on each frame where they happen: a small round hole inside the person is filled, and a stray bit of the room
near the top of the head (a lamp, a ceiling mark) is removed. The model file lives in the runtime's model
folder (AVS_MODELS, set by the installer), in <engine>/models, or next to this script.
"""
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import reel_config  # noqa: E402

W, H, FPS = 1080, 1920, 30
MODEL_NAME = 'selfie_multiclass_256x256.tflite'
BLEND = 0.2        # share of the previous frame's mask kept (temporal smoothing)
PAD = 0.12         # padding around the person box for the crop pass
GF_R, GF_EPS = 6, 2e-3   # guided filter radius (px) and regularisation
LD_ERODE, LD_FEATHER = 2, 1   # lights-down edge: pulled in this many px, then softened by a box of this radius (twice)
HOLE_MAX, HOLE_ROUND = 900, 3.0     # clean(): a hole up to this many pixels, no more than 3x longer than wide, is filled
SPECK_MAX, SPECK_TOP = 2500, 0.06   # clean(): a stray bit up to this size, ending above the head top + 6% of the person, goes
                                    # (measured: a lamp beside a cap ends by 5.1%, the bits of a hand waved by the head from 6.4%)
SPECK_GAP = 20                      # clean(): ...and at least this many px clear of the person (a curl of hair sits closer)
CLEAN_TAG = 'clean-h%d-s%d-t%d-g%d-soft' % (HOLE_MAX, SPECK_MAX, round(SPECK_TOP * 100), SPECK_GAP)
LD_TAG = 'ld-e%d-f%d-body' % (LD_ERODE, LD_FEATHER)   # part of the reuse stamp, so a changed edge recuts


def fg_path(stem, a, b):
    return os.path.join(ROOT, 'public', 'host', '%s-fg-%d-%d.webm' % (stem, a, b))


def model_path():
    for d in (os.environ.get('AVS_MODELS'), os.path.join(ROOT, 'models'), HERE):
        if d and os.path.exists(os.path.join(d, MODEL_NAME)):
            return os.path.join(d, MODEL_NAME)
    sys.exit('matte: the cutout model %s is missing (looked in AVS_MODELS, models/ and scripts/). Run the installer cutout step.' % MODEL_NAME)


def box(a, r):
    """Box mean of radius r through an integral image (edges padded)."""
    import numpy as np
    k = 2 * r + 1
    pad = np.pad(a, r, mode='edge')
    c = np.pad(np.cumsum(np.cumsum(pad, 0, dtype=np.float64), 1), ((1, 0), (1, 0)))
    return ((c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)).astype(np.float32)


def erode(a, r):
    """Soft erosion: each pixel takes the lowest value within a disk of radius r."""
    import numpy as np
    out = a.copy()
    p = np.pad(a, r, mode='edge')
    h, w = a.shape
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if (dx or dy) and dx * dx + dy * dy <= r * r:
                np.minimum(out, p[r + dy:r + dy + h, r + dx:r + dx + w], out=out)
    return out


def fill_down(mask):
    """The body below the shoulders, made whole: from the first row as wide as the shoulders down, every column that has
    the person in it stays the person to the bottom of the frame. The small model drops parts of a torso behind a hand or a
    child it is holding, and a hole in the body reads as a dark blotch once the room dims. The head and hair stay as cut."""
    import numpy as np
    on = mask > 0.5
    wide = on.sum(1)
    if not wide.any():
        return mask
    y = int(np.argmax(wide >= 0.8 * wide.max()))
    body = np.maximum.accumulate(on[y:], axis=0)
    out = mask.copy()
    out[y:] = np.maximum(out[y:], body.astype(np.float32))
    return out


def clean(mask):
    """Two kinds of small cutout misses, fixed per frame and only where they are (a fix over the whole clip would make the
    edge flicker). A hole inside the person this small and round (a miss on a shirt, a seat belt, hair) is filled, so the
    words behind never show through the body. A stray bit of the room this small, near or above the top of the head and
    well inside the frame, and clear of the person (a lamp, a ceiling mark), is removed, so it never draws a patch of wall over the words. Long
    gaps (between an arm and the body, between legs) are real and stay open, and a piece of a hand coming in from the
    frame's edge stays. Measured on 25 cutouts, 2026-11-23. Returns (mask, holes filled, specks removed)."""
    import cv2
    import numpy as np
    on = (mask > 0.5).astype(np.uint8)
    if on.sum() < 1000:
        return mask, 0, 0
    h, w = on.shape
    edge = lambda s: s[0] == 0 or s[1] == 0 or s[0] + s[2] >= w or s[1] + s[3] >= h  # noqa: E731  (touches the frame)
    out = mask
    k, lab, st, _ = cv2.connectedComponentsWithStats(1 - on, connectivity=4)
    holes = [i for i in range(1, k) if not edge(st[i]) and st[i][4] <= HOLE_MAX and max(st[i][2], st[i][3]) <= HOLE_ROUND * min(st[i][2], st[i][3])]
    if holes:
        fill = cv2.dilate(np.isin(lab, holes).astype(np.uint8), np.ones((5, 5), np.uint8))
        out = np.maximum(out, fill.astype(np.float32))
    # stray bits are found on the soft outline (alpha above 0.15), so a bit and its faint rim are one piece: it goes whole
    # or stays whole, never leaving half an arc behind
    k, lab, st, _ = cv2.connectedComponentsWithStats((mask > 0.15).astype(np.uint8), connectivity=8)
    specks = []
    if k > 2:
        # the person can come out in more than one big piece (a raised arm, a head cut off at the neck): every big piece
        # is the person, so its top, its height and the distance are measured from all of them
        largest = int(st[1:, 4].max())
        body = [i for i in range(1, k) if st[i][4] >= min(largest, max(4 * SPECK_MAX, 0.05 * largest))]   # the largest always
        top = min(st[i][1] for i in body)
        tall = max(st[i][1] + st[i][3] for i in body) - top
        inside = lambda q: q[0] >= SPECK_GAP * 2 and q[1] >= SPECK_GAP * 2 and q[0] + q[2] <= w - SPECK_GAP * 2 and q[1] + q[3] <= h - SPECK_GAP * 2  # noqa: E731
        # (40 px clear of the frame: a hand coming in, or someone walking out, leaves bits by the edge)
        cand = [i for i in range(1, k) if i not in body and inside(st[i]) and st[i][4] <= SPECK_MAX and st[i][1] + st[i][3] <= top + SPECK_TOP * tall]
        if cand:   # how far each one sits from the person: bits of hair are a few px off it, a lamp or a ceiling mark well clear
            person = np.isin(lab, body)
            far = cv2.distanceTransform((~person).astype(np.uint8), cv2.DIST_L2, 3)
            for i in cand:
                x, y, bw, bh = st[i][:4]
                if far[y:y + bh, x:x + bw][lab[y:y + bh, x:x + bw] == i].min() >= SPECK_GAP:
                    specks.append(i)
    if specks:
        # 7 px past it takes its soft rim too (a removed bit is at least SPECK_GAP clear of the person, so this never reaches them)
        gone = cv2.dilate(np.isin(lab, specks).astype(np.uint8), np.ones((15, 15), np.uint8)) * (~person)
        out = out * (1 - gone.astype(np.float32))
    return out, len(holes), len(specks)


def guided(mask, guide, r, eps):
    """Guided filter (He et al.): the mask takes its edges from the gray picture."""
    m_i, m_p = box(guide, r), box(mask, r)
    a = (box(guide * mask, r) - m_i * m_p) / (box(guide * guide, r) - m_i * m_i + eps)
    b = m_p - a * m_i
    return box(a, r) * guide + box(b, r)


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    name = sys.argv[1]
    cfg = reel_config.load(name)
    items = list(cfg.get('backText') or [])
    items += [{'in': e['in'], 'out': e['out'], 'ld': True} for e in cfg.get('effects') or [] if e.get('kind') == 'lights-down']
    th = cfg.get('thumbnail')
    if th:
        items.append({'in': int(th['frame']), 'out': int(th['frame']) + 1, 'thumb': True})
    cv = cfg.get('cover') or {}
    if cv.get('back') and cfg.get('placement') != 'paid' and not (th and int(th['frame']) == int(cv['frame'])):   # a words-behind cover: the same one-frame cutout
        items.append({'in': int(cv['frame']), 'out': int(cv['frame']) + 1, 'thumb': True})
    if not items:
        print('matte: %s has no backText, lights-down, thumbnail or words-behind cover, nothing to do' % name)
        return
    cut = os.path.join(ROOT, 'public', reel_config.host_file(cfg))   # the color-graded picture when there is one
    stem = reel_config.stem(cfg)
    cut_id = hashlib.sha1(open(cut, 'rb').read(1 << 20) + str(os.path.getsize(cut)).encode()).hexdigest()[:12]
    todo = []
    for it in items:
        a, b = int(it['in']), int(it['out'])
        out = (os.path.join(ROOT, 'public', 'host', '%s-thumb-%d.png' % (stem, a)) if it.get('thumb') else
               os.path.join(ROOT, 'public', 'host', '%s-fg-ld-%d-%d.webm' % (stem, a, b)) if it.get('ld') else fg_path(stem, a, b))
        stamp = out + '.src'
        want = cut_id + ' ' + CLEAN_TAG + (' ' + LD_TAG if it.get('ld') else '')
        if os.path.exists(out) and os.path.exists(stamp) and open(stamp).read().strip() == want:
            print('matte: reuse %s' % os.path.relpath(out, ROOT))
            continue
        todo.append((a, b, out, stamp, want, bool(it.get('ld'))))
    if not todo:
        return

    import numpy as np
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions
    from mediapipe.tasks.python.vision import ImageSegmenter, ImageSegmenterOptions, RunningMode
    opts = ImageSegmenterOptions(base_options=BaseOptions(model_asset_path=model_path()), running_mode=RunningMode.VIDEO,
                                 output_confidence_masks=True, output_category_mask=False)
    def person(seg, rgb, ts):
        res = seg.segment_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb)), ts)
        m = [np.asarray(x.numpy_view()).reshape(rgb.shape[0], rgb.shape[1]) for x in res.confidence_masks]
        return 1.0 - m[0] if len(m) > 1 else m[0]   # class 0 is the background

    import time
    for a, b, out, stamp, want, ld in todo:
        t0 = time.time()
        seg_full, seg_crop = ImageSegmenter.create_from_options(opts), ImageSegmenter.create_from_options(opts)
        # frames by TIME, not index: a cut spliced from many takes can drop a frame at a join, and
        # the renderer seeks by time, so the cutout must match it or the host appears twice
        rd = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', cut, '-vf', 'fps=%d,select=between(n\\,%d\\,%d)' % (FPS, a, b - 1),
                               '-fps_mode', 'passthrough', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
        codec = (['-frames:v', '1', '-pix_fmt', 'rgba'] if out.endswith('.png') else
                 ['-c:v', 'libvpx-vp9', '-pix_fmt', 'yuva420p', '-b:v', '0', '-crf', '18', '-row-mt', '1',
                  '-deadline', 'good', '-cpu-used', '4', '-auto-alt-ref', '0'])
        enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', '%dx%d' % (W, H),
                                '-r', str(FPS), '-i', '-'] + codec + [out], stdin=subprocess.PIPE)
        prev, done, holes, specks = None, 0, 0, 0
        for k in range(b - a):
            buf = rd.stdout.read(W * H * 3)
            if len(buf) < W * H * 3:
                break
            rgb = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
            ts = int(k * 1000 / FPS)
            mask = person(seg_full, rgb, ts)
            ys, xs = np.where(mask > 0.5)
            if len(ys):                                   # second pass on a crop around the person
                y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
                ph, pw = int((y1 - y0) * PAD), int((x1 - x0) * PAD)
                y0, y1, x0, x1 = max(0, y0 - ph), min(H, y1 + ph), max(0, x0 - pw), min(W, x1 + pw)
                mask = np.zeros((H, W), np.float32)
                mask[y0:y1, x0:x1] = person(seg_crop, rgb[y0:y1, x0:x1], ts)
            gray = (rgb.astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32)) / 255.0
            mask = guided(mask.astype(np.float32), gray, GF_R, GF_EPS)
            mask = np.clip((mask - 0.3) / 0.4, 0, 1)
            mask = mask * mask * (3 - 2 * mask)               # smoothstep: a tight, soft edge
            if prev is not None:
                mask = (1 - BLEND) * mask + BLEND * prev
            prev = mask
            mask, nh, ns = clean(mask)   # small holes filled, stray bits of the room removed, this frame only
            holes += nh
            specks += ns
            if ld:   # a dark room: the body made whole, the edge pulled in off the background, then feathered
                mask = erode(fill_down(mask), LD_ERODE)
                for _ in range(2):
                    mask = box(mask, LD_FEATHER)
            enc.stdin.write(np.dstack([rgb, (mask * 255).astype(np.uint8)]).tobytes())
            done += 1
        rd.stdout.close(); rd.wait(); enc.stdin.close(); enc.wait(); seg_full.close(); seg_crop.close()
        if done != b - a:
            sys.exit('matte: %s got %d of %d frames' % (out, done, b - a))
        open(stamp, 'w').write(want)
        print('matte: %s (%d frames, %.1fs, %d small holes filled, %d stray bits removed)' % (os.path.relpath(out, ROOT), done, time.time() - t0, holes, specks))


if __name__ == '__main__':
    if '--help' in sys.argv[1:] or sys.argv[1:2] == ['-h']:   # --help: the usage, nothing else
        print((__doc__ or '').strip() or 'usage: python3 scripts/%s' % os.path.basename(__file__))
        sys.exit(0)
    main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
