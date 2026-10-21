#!/usr/bin/env python3
"""Foreground cutouts for BACK TEXT (big highlighted words that sit behind the host).

    "$DVE_MATTE_PYTHON" scripts/matte_reel.py <name>

For every entry in the config's "backText", cuts the host out of the cut over that entry's
frames with MediaPipe's selfie segmenter (Apache-2.0, runs locally) and writes
public/host/<stem>-fg-<in>-<out>.webm: the same pixels as the cut, with an alpha channel that
keeps only the person. The engine draws  footage -> back text -> this cutout,  so the words
read as standing in the room behind the host. The thumbnail cutout is one frame, written as a
PNG. Only the listed frames are processed. Cutouts are reused while the cut and the range are
unchanged.

The segmenter runs twice per frame: once on the full frame to find the person, once on a
crop around them (four times the detail per pixel). A guided filter then pulls the mask edge
onto the real edges in the picture, and a light temporal blend keeps it steady between frames. The model file lives in the runtime's model
folder (DVE_MODELS, set by the installer), in <engine>/models, or next to this script.
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


def fg_path(stem, a, b):
    return os.path.join(ROOT, 'public', 'host', '%s-fg-%d-%d.webm' % (stem, a, b))


def model_path():
    for d in (os.environ.get('DVE_MODELS'), os.path.join(ROOT, 'models'), HERE):
        if d and os.path.exists(os.path.join(d, MODEL_NAME)):
            return os.path.join(d, MODEL_NAME)
    sys.exit('matte: the cutout model %s is missing (looked in DVE_MODELS, models/ and scripts/). Run the installer cutout step.' % MODEL_NAME)


def box(a, r):
    """Box mean of radius r through an integral image (edges padded)."""
    import numpy as np
    k = 2 * r + 1
    pad = np.pad(a, r, mode='edge')
    c = np.pad(np.cumsum(np.cumsum(pad, 0, dtype=np.float64), 1), ((1, 0), (1, 0)))
    return ((c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)).astype(np.float32)


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
    th = cfg.get('thumbnail')
    if th:
        items.append({'in': int(th['frame']), 'out': int(th['frame']) + 1, 'thumb': True})
    if not items:
        print('matte: %s has no backText or thumbnail, nothing to do' % name)
        return
    cut = os.path.join(ROOT, 'public', cfg['src'])
    stem = reel_config.stem(cfg)
    cut_id = hashlib.sha1(open(cut, 'rb').read(1 << 20) + str(os.path.getsize(cut)).encode()).hexdigest()[:12]
    todo = []
    for it in items:
        a, b = int(it['in']), int(it['out'])
        out = os.path.join(ROOT, 'public', 'host', '%s-thumb-%d.png' % (stem, a)) if it.get('thumb') else fg_path(stem, a, b)
        stamp = out + '.src'
        if os.path.exists(out) and os.path.exists(stamp) and open(stamp).read().strip() == cut_id:
            print('matte: reuse %s' % os.path.relpath(out, ROOT))
            continue
        todo.append((a, b, out, stamp))
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

    for a, b, out, stamp in todo:
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
        prev, done = None, 0
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
            enc.stdin.write(np.dstack([rgb, (mask * 255).astype(np.uint8)]).tobytes())
            done += 1
        rd.stdout.close(); rd.wait(); enc.stdin.close(); enc.wait(); seg_full.close(); seg_crop.close()
        if done != b - a:
            sys.exit('matte: %s got %d of %d frames' % (out, done, b - a))
        open(stamp, 'w').write(cut_id)
        print('matte: %s (%d frames)' % (os.path.relpath(out, ROOT), done))


if __name__ == '__main__':
    main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
