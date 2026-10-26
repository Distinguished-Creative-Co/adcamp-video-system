#!/usr/bin/env python3
"""Post-render gates: the rendered file does what the config declares.

    python3 scripts/verify_reel.py <name> out/<name>.mp4

MEASURED on the render, against the cut footage (ffmpeg sampling, grayscale):
  probe      1080x1920, 30 fps, frame count and duration match the config, audio present
  open       frame 0 matches the source punched in at open.scale better than at 1.0,
             and just after the open the frame matches the source at about 1.0
  card       every settled window scene shows the SOURCE inside the card rect (face-anchored)
  inset      every settled swap shows the source inside the panel inset
  safe       in settled window/swap frames nothing bright sits under the IG UI strips
  motion     no frozen stretch: frames 0.5s apart always differ

Presence frame by frame and footage-edge math are proven on the state machine by
scripts/test_layout.mjs. The gates are not the edit: the stills are.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import reel_config  # noqa: E402

GLIDE_F, SWAP_F = 20, 18
CARD = (240, 800, 600, 760)
PANEL = (60, 140, 900, 1420)
INSET = (56, 996, 280, 360)
SW, SH = 150, 190        # sample size for card-shaped regions


def grab(mp4, t, crop=None, size=(SW, SH), scale_first=None):
    vf = []
    if scale_first:
        vf.append(scale_first)
    if crop:
        vf.append('crop=%d:%d:%d:%d' % (crop[2], crop[3], crop[0], crop[1]))
    vf.append('scale=%d:%d' % size)
    p = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-ss', '%.3f' % t, '-i', mp4, '-frames:v', '1',
                        '-vf', ','.join(vf), '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], capture_output=True)
    n = size[0] * size[1]
    if p.returncode or len(p.stdout) < n:
        raise RuntimeError('sample failed @%.2fs: %s' % (t, p.stderr.decode()[-200:]))
    return p.stdout[:n]


GRADED = False   # set in main(): the reel grades the host, so compare structure, not raw levels


def diff(a, b):
    """Mean absolute gray-level difference. For a graded reel the render (a) is first matched
    to the source's mean and spread, so a look (darker, more contrast) is not read as the
    wrong frame, while a different frame or framing still differs."""
    if GRADED:
        n = float(len(a))
        ma, mb = sum(a) / n, sum(b) / n
        sa = (sum((x - ma) ** 2 for x in a) / n) ** 0.5 or 1.0
        sb = (sum((y - mb) ** 2 for y in b) / n) ** 0.5 or 1.0
        return sum(abs((x - ma) / sa * sb + mb - y) for x, y in zip(a, b)) / n
    return sum(abs(x - y) for x, y in zip(a, b)) / float(len(a))


def src_crop(cfg, view, zoom):
    """Source-pixel rectangle a face-anchored cover view shows (mirrors layout.place)."""
    vx, vy, vw, vh, ax, ay = view
    sw, sh = cfg['source']['w'], cfg['source']['h']
    s = max(vw / float(sw), vh / float(sh)) * zoom
    tx = min(max(ax * vw - cfg['faceX'] * s, vw - sw * s), 0)
    ty = min(max(ay * vh - cfg['faceY'] * s, vh - sh * s), 0)
    return (int(round(-tx / s)), int(round(-ty / s)), int(round(vw / s)), int(round(vh / s)))


def best_match(cfg, out, src, t, region, view_wh, zooms, dys, size):
    """Lowest diff between the render region and the face-anchored source over a small sweep."""
    rx, ry, rw, rh = region
    # graded reels: the vignette darkens the region's edges non-linearly, so compare the
    # centre (measured 2026-10-01: right frame ~10, frames 2-5s away 20-32, limit 18)
    k = int(0.15 * min(rw, rh)) if GRADED else 0
    best = (1e9, None)
    for dy in dys:
        r = grab(out, t, (rx + k, ry + dy + k, rw - 2 * k, rh - 2 * k), size)
        for z in zooms:
            c = src_crop(cfg, (0, 0, view_wh[0], view_wh[1], 0.5, 0.48), z)
            if k:
                sx, sy = c[2] / float(view_wh[0]), c[3] / float(view_wh[1])
                c = (c[0] + k * sx, c[1] + k * sy, c[2] - 2 * k * sx, c[3] - 2 * k * sy)
            d = diff(r, grab(src, t, c, size))
            if d < best[0]:
                best = (d, (z, dy))
    return best


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    name, out = sys.argv[1], sys.argv[2]
    cfg = reel_config.load(name)
    global GRADED
    GRADED = bool(cfg.get('grade'))
    src = os.path.join(ROOT, 'public', reel_config.host_file(cfg))   # compare against the picture as drawn (graded or not)
    fails, notes = [], []

    pr = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-print_format', 'json', '-show_streams', '-show_format', out],
                                   capture_output=True, text=True, check=True).stdout)
    v = [s for s in pr['streams'] if s['codec_type'] == 'video'][0]
    has_audio = any(s['codec_type'] == 'audio' for s in pr['streams'])
    nb = int(v.get('nb_frames', 0) or 0)
    fps = eval(v['r_frame_rate'])  # "30/1"
    dur = float(pr['format']['duration'])
    if (int(v['width']), int(v['height'])) != (1080, 1920):
        fails.append('size %sx%s, want 1080x1920' % (v['width'], v['height']))
    if abs(fps - 30) > 0.01:
        fails.append('fps %.3f, want 30' % fps)
    if nb and abs(nb - cfg['frames']) > 1:
        fails.append('%d frames, config says %d' % (nb, cfg['frames']))
    if not has_audio:
        fails.append('no audio track')
    notes.append('probe: %sx%s, %.2f fps, %s frames, %.2fs, audio %s' % (v['width'], v['height'], fps, nb or '?', dur, 'yes' if has_audio else 'NO'))

    # open: punched in at frame 0, settled after the open (region above the caption band)
    top = (0, 0, 1080, 1150)
    def full_diff(t, z):
        c = src_crop(cfg, (0, 0, 1080, 1920, cfg['faceX'] / 1080.0, cfg['faceY'] / 1920.0), z)
        s_top = (c[0], c[1], c[2], int(round(c[3] * 1150 / 1920.0)))
        return diff(grab(out, t, top, (108, 115)), grab(src, t, s_top, (108, 115)))
    t_open = (1 / 30.0) if cfg.get('cover') else 0.0   # frame 0 is the cover when one is set
    zo = cfg['open']['scale'] - (cfg['open']['scale'] - 1) * (1 - (1 - 1.0 / cfg['open']['frames']) ** 3) if cfg.get('cover') else cfg['open']['scale']
    d_open, d_flat = full_diff(t_open, zo), full_diff(t_open, 1.0)
    t_set = (cfg['open']['frames'] + 3) / 30.0
    d_set = min(full_diff(t_set, z) for z in (1.0, 1.005, 1.01))
    notes.append('open: frame %d diff %.1f at %.2fx vs %.1f at 1.0; settled diff %.1f' % (round(t_open * 30), d_open, zo, d_flat, d_set))
    if cfg['open']['scale'] > 1.001 and not d_open < d_flat:   # an open of 1.0 asks for no punch-in
        fails.append('open: the first frame of the open is not punched in')
    if cfg.get('cover'):
        c = cfg['cover']
        d_cov = diff(grab(out, 0.0, (0, 0, 1080, 1100), (108, 110)), grab(src, c['frame'] / 30.0, (0, 0, 1080, 1100), (108, 110)))
        notes.append('cover: frame 0 vs source frame %d diff %.1f' % (c['frame'], d_cov))
        if d_cov > 12:
            fails.append('cover: frame 0 does not show source frame %d (diff %.1f)' % (c['frame'], d_cov))
    if d_set > 12:
        fails.append('open: not settled to 1.0 after %d frames (diff %.1f)' % (cfg['open']['frames'], d_set))

    # card at rest in each window scene, outside swaps
    swaps = cfg['swaps']
    def in_swap(f):
        return any(s['in'] - 2 <= f <= (s['out'] + SWAP_F + 2 if s['out'] < cfg['frames'] else cfg['frames']) for s in swaps)
    for i, sc in enumerate(cfg['scenes']):
        if sc['mode'] != 'window':
            continue
        f = sc['from'] + GLIDE_F + 12
        if in_swap(f):
            f = next((s['out'] + SWAP_F + 12 for s in swaps if s['in'] - 2 <= f <= s['out'] + SWAP_F + 2 and s['out'] < cfg['frames']), None)
            nxt = min([x['from'] for x in cfg['scenes'] if x['from'] > sc['from']] + [cfg['frames']])
            if f is None or f >= nxt - GLIDE_F:   # the panel holds until the scene ends: no card at rest to check
                notes.append('card, scene %d: panel holds the whole scene, no resting card to check' % (i + 1))
                continue
        d, arg = best_match(cfg, out, src, f / 30.0, CARD, (600, 760), (1.0, 1.01, 1.02, 1.03), (-3, 0, 3), (SW, SH))
        notes.append('card, scene %d @%df: diff %.1f (zoom %.2f, dy %d)' % (i + 1, f, d, arg[0], arg[1]))
        if d > 18:
            fails.append('card, scene %d: the card does not show the face-anchored source (diff %.1f)' % (i + 1, d))

    # inset during each settled swap
    for i, s in enumerate(swaps):
        f = s['in'] + SWAP_F + 12
        region = (PANEL[0] + INSET[0], PANEL[1] + INSET[1], INSET[2], INSET[3])
        d, arg = best_match(cfg, out, src, f / 30.0, region, (280, 360), (1.0, 1.01, 1.02, 1.03), (-6, -3, 0, 3, 6), (70, 90))
        notes.append('inset, swap %d @%df: diff %.1f' % (i + 1, f, d))
        if d > 22:
            fails.append('inset, swap %d: no host in the panel inset (diff %.1f)' % (i + 1, d))

    # safe zones: settled window/swap frames, strips under the IG UI stay dark
    bad_safe = []
    for i, sc in enumerate(cfg['scenes']):
        if sc['mode'] != 'window':
            continue
        end = cfg['scenes'][i + 1]['from'] if i + 1 < len(cfg['scenes']) else cfg['frames']
        for f in range(sc['from'] + GLIDE_F + 4, end - 2, 45):
            if any(0 <= f - s['in'] < SWAP_F + 2 or (s['out'] < cfg['frames'] and 0 <= f - s['out'] < SWAP_F + 2) for s in swaps):
                continue
            right = grab(out, f / 30.0, (964, 0, 116, 1920), (29, 480))
            bottom = grab(out, f / 30.0, (0, 1604, 1080, 316), (270, 79))
            for lab, buf in (('right', right), ('bottom', bottom)):
                # content, not brightness: text or a panel edge stands out from the strip's own
                # background (dark charcoal OR light paper), so count pixels far from the median
                srt = sorted(buf)
                med = srt[len(srt) // 2]
                off = sum(1 for v in buf if abs(v - med) > 70) / float(len(buf))
                if off > 0.004:
                    bad_safe.append('%s strip @%df (%.1f%% of pixels stand out from the background)' % (lab, f, 100 * off))
    notes.append('safe zones: %s' % ('clean' if not bad_safe else '%d hits' % len(bad_safe)))
    fails += ['safe zone: ' + b for b in bad_safe[:6]]

    # motion: never a frozen stretch
    frozen = []
    # a slide card fills the frame and holds still by design (the speaker talks in a small corner window)
    slides = [(e['in'] / 30.0, e['out'] / 30.0) for e in cfg.get('effects', []) if e.get('kind') == 'card']
    t = 0.25
    while t + 0.5 < dur - 0.1:
        if any(a - 0.5 <= t <= b for a, b in slides):
            t += 1.0
            continue
        d = diff(grab(out, t, None, (108, 192)), grab(out, t + 0.5, None, (108, 192)))
        if d < 0.3:
            frozen.append('%.2fs (diff %.2f)' % (t, d))
        t += 1.0
    if slides:
        notes.append('motion: %d slide card(s) skipped, they hold still by design' % len(slides))
    notes.append('motion: %s' % ('always moving' if not frozen else 'frozen at ' + ', '.join(frozen[:5])))
    fails += ['frozen: ' + x for x in frozen[:5]]

    # audio: loudness contract, then drift against the cut
    lt = subprocess.run(['ffmpeg', '-hide_banner', '-i', out, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json',
                         '-f', 'null', '-'], capture_output=True, text=True).stderr
    import re as _re
    lj = json.loads(_re.search(r'\{\s*"input_i".*?\}', lt, _re.S).group())
    li, tp = float(lj['input_i']), float(lj['input_tp'])
    notes.append('loudness: %.1f LUFS integrated, true peak %.1f dBTP' % (li, tp))
    if not -15.0 <= li <= -13.0:
        fails.append('loudness %.1f LUFS, want -14 +/- 1' % li)
    if tp > -1.0:
        fails.append('true peak %.1f dBTP is above -1' % tp)
    try:
        import numpy as np

        def pcm(path, t0, d):
            p = subprocess.run(['ffmpeg', '-v', 'error', '-ss', '%.3f' % t0, '-t', '%.3f' % d, '-i', path, '-vn', '-ac', '1',
                                '-ar', '8000', '-f', 's16le', '-'], capture_output=True)
            return np.frombuffer(p.stdout, dtype=np.int16).astype(np.float64)
        worst = 0.0
        for t0 in (0.5, max(0.5, dur / 2 - 3), max(0.5, dur - 7)):
            a, b = pcm(out, t0, 6.0), pcm(src, t0, 6.0)
            n = min(len(a), len(b))
            a, b = a[:n] - a[:n].mean(), b[:n] - b[:n].mean()
            maxlag = 2000                                # +/- 0.25s at 8 kHz
            best, lag = -1.0, 0
            fa, fb = np.fft.rfft(a, 2 * n), np.fft.rfft(b, 2 * n)
            xc = np.fft.irfft(fa * np.conj(fb))
            xc = np.concatenate([xc[-maxlag:], xc[:maxlag + 1]])
            k = int(np.argmax(xc))
            lag = k - maxlag
            best = xc[k] / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-9)
            worst = max(worst, abs(lag) / 8000.0)
            notes.append('audio vs cut @%.1fs: offset %+.1f ms, correlation %.3f' % (t0, 1000 * lag / 8000.0, best))
            if abs(lag) > 160 or best < 0.8:            # > 20 ms of drift, or not the same narration
                fails.append('audio drift @%.1fs: offset %+.1f ms, correlation %.3f' % (t0, 1000 * lag / 8000.0, best))
    except ImportError:
        notes.append('audio drift: skipped (numpy not available)')

    print('\nVERIFY %s -> %s' % (name, out))
    for n in notes:
        print('  ' + n)
    rec = {'file': out, 'notes': notes, 'fails': fails}
    os.makedirs(os.path.join(ROOT, 'qa', name), exist_ok=True)
    json.dump(rec, open(os.path.join(ROOT, 'qa', name, 'verify.json'), 'w'), indent=1)
    if fails:
        print('FAIL (%d)' % len(fails))
        for f in fails:
            print('  - ' + f)
        sys.exit(1)
    print('PASS')


if __name__ == '__main__':
    main()
