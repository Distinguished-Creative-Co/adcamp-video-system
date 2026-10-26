#!/usr/bin/env python3
"""Study an example reel from start to finish, as pictures to LOOK at plus the numbers that can be measured.

    "$AVS_MATTE_PYTHON" scripts/study_example.py <file> [--step 0.5] [--no-words]

Writes styles/_examples/<file stem>/ (run it with the cutout Python: it has Pillow and numpy):
  sheet_01.jpg ...  every sampled frame with its time, 12 to a sheet, in order. Read ALL of them: captions,
                    graphics and framing change from beat to beat, three stills are a guess
  cuts.jpg          the frame just before and just after each cut, side by side
  motion_01.jpg ... frame-by-frame strips (15 a second) around the moments something appears or moves, the
                    opening first: these show HOW captions and graphics animate, which sheets can't
  study.json        length, size, cut times and shot lengths, pace, loudness every 0.1 s, sound jumps,
                    the words with their times (speech rate, pauses)
  frames/           the sampled frames at full size, for a close look at type and color
It prints the measured half. The seen half (typeface feel, case, color, plates, placement, how words arrive,
graphic elements, grade) is for the editor reading the pictures.
"""
import json
import math
import os
import re
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def probe(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,r_frame_rate:format=duration',
                          '-of', 'json', path], capture_output=True, text=True).stdout
    d = json.loads(out)
    st = d['streams'][0]
    n, den = st['r_frame_rate'].split('/')
    return float(d['format']['duration']), st['width'], st['height'], float(n) / float(den or 1)


def grab(path, t, w):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', '%.3f' % max(0, t), '-i', path, '-frames:v', '1', '-vf', 'scale=%d:-2' % w,
                          '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True).stdout
    import io
    return Image.open(io.BytesIO(raw)).convert('RGB') if raw else None


def font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def label(img, text):
    d = ImageDraw.Draw(img)
    f = font(max(14, img.width // 14))
    x0, y0, x1, y1 = d.textbbox((0, 0), text, font=f)
    d.rectangle((0, 0, x1 - x0 + 12, y1 - y0 + 10), fill=(0, 0, 0))
    d.text((6 - x0, 5 - y0), text, font=f, fill=(255, 255, 0))
    return img


def tile(imgs, cols, out, pad=6):
    if not imgs:
        return
    w, h = imgs[0].size
    rows = math.ceil(len(imgs) / cols)
    sheet = Image.new('RGB', (cols * w + (cols + 1) * pad, rows * h + (rows + 1) * pad), (24, 24, 24))
    for i, im in enumerate(imgs):
        sheet.paste(im.resize((w, h)), (pad + (i % cols) * (w + pad), pad + (i // cols) * (h + pad)))
    sheet.save(out, quality=88)


def scene_cuts(path):
    t = subprocess.run(['ffmpeg', '-hide_banner', '-i', path, '-vf', "select='gt(scene,0.32)',showinfo", '-an', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    return [round(float(x), 3) for x in re.findall(r'pts_time:([\d.]+)', t)]


def low_res_motion(path, dur, fps=10):
    """Mean frame-to-frame change at 10 fps on a small gray copy: where something appears or moves."""
    w, h = 90, 160
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-vf', 'fps=%d,scale=%d:%d,format=gray' % (fps, w, h), '-f', 'rawvideo', '-'],
                         capture_output=True).stdout
    n = len(raw) // (w * h)
    if n < 2:
        return []
    a = np.frombuffer(raw[:n * w * h], np.uint8).reshape(n, h, w).astype(np.int16)
    diff = np.abs(np.diff(a, axis=0)).mean(axis=(1, 2))
    return [((i + 1) / fps, float(v)) for i, v in enumerate(diff)]


def loudness(path):
    t = subprocess.run(['ffmpeg', '-hide_banner', '-i', path, '-vn', '-af', 'aresample=16000,asetnsamples=1600,astats=metadata=1:reset=1,'
                        'ametadata=print:key=lavfi.astats.Overall.RMS_level', '-f', 'null', '-'], capture_output=True, text=True).stderr
    vals = []
    for m in re.findall(r'RMS_level=(-?[\d.]+|-inf)', t):
        vals.append(-90.0 if m == '-inf' else max(-90.0, float(m)))
    return [round(v, 1) for v in vals]   # one value per 0.1 s


def words_of(path):
    py = os.environ.get('AVS_PYTHON') or os.path.expanduser('"$AVS_PYTHON"')
    if not os.path.exists(py):
        return None
    code = ('import json,sys,faster_whisper as fw\n'
            'seg,_=fw.WhisperModel("base",device="cpu",compute_type="int8").transcribe(sys.argv[1],word_timestamps=True,vad_filter=True)\n'
            'print(json.dumps([[w.word.strip(),round(w.start,2),round(w.end,2)] for s in seg for w in (s.words or [])]))\n')
    p = subprocess.run([py, '-c', code, path], capture_output=True, text=True)
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return None


def main():
    a = sys.argv[1:]
    files = [x for i, x in enumerate(a) if not x.startswith('--') and (i == 0 or a[i - 1] != '--step')]
    if len(files) != 1:
        sys.exit(__doc__)
    src = os.path.abspath(os.path.expanduser(files[0]))
    step = float(a[a.index('--step') + 1]) if '--step' in a else 0.5
    out = os.path.join(ROOT, 'styles', '_examples', os.path.splitext(os.path.basename(src))[0])
    os.makedirs(os.path.join(out, 'frames'), exist_ok=True)

    if src.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
        im = Image.open(src).convert('RGB')
        im.save(os.path.join(out, 'frames', 'still.jpg'), quality=92)
        w, h = im.size
        crop = im.crop((w // 4, h // 4, 3 * w // 4, 3 * h // 4)).resize((w // 2 * 2 // 2, h // 2 * 2 // 2))
        tile([im.resize((540, int(540 * h / w))), crop.resize((540, int(540 * h / w)))], 2, os.path.join(out, 'sheet_01.jpg'))
        json.dump({'kind': 'still', 'size': [w, h]}, open(os.path.join(out, 'study.json'), 'w'), indent=1)
        print('study: a still (%dx%d). Read %s/sheet_01.jpg: it shows type, color, plate and placement, not motion or sound.' % (w, h, out))
        return

    dur, W, H, fps = probe(src)
    if dur > 8:
        step = max(step, dur / 96)
    times = [round(t, 2) for t in np.arange(0, max(dur - 0.05, 0.01), step)]
    frames = []
    for i, t in enumerate(times):
        im = grab(src, t, 540)
        if im is None:
            continue
        big = grab(src, t, min(W, 1080))
        if big:
            big.save(os.path.join(out, 'frames', 'f_%03d_%06.2f.jpg' % (i, t)), quality=90)
        frames.append(label(im, '%.1fs' % t))
    for k in range(0, len(frames), 12):
        tile(frames[k:k + 12], 4, os.path.join(out, 'sheet_%02d.jpg' % (k // 12 + 1)))

    cuts = scene_cuts(src)
    pairs = []
    for c in cuts[:24]:
        a1, b1 = grab(src, c - 0.07, 300), grab(src, c + 0.07, 300)
        if a1 and b1:
            pairs += [label(a1, 'before %.2fs' % c), label(b1, 'after')]
    tile(pairs, 4, os.path.join(out, 'cuts.jpg'))

    motion = low_res_motion(src, dur)
    near_cut = lambda t: any(abs(t - c) < 0.25 for c in cuts)
    peaks = []
    for i, (t, v) in enumerate(motion):
        if near_cut(t) or v < 2.5:
            continue
        lo = motion[max(0, i - 3):i + 4]
        if v >= max(x[1] for x in lo) and all(abs(t - p) > 1.2 for p, _ in peaks):
            peaks.append((t, v))
    peaks = sorted(peaks, key=lambda x: -x[1])[:7]
    moments = sorted({0.0} | {round(t, 2) for t, _ in peaks})
    for n, t in enumerate(moments[:8], 1):
        strip = [label(grab(src, t - 0.1 + j / 15, 240), '%.2f' % (t - 0.1 + j / 15)) for j in range(8)]
        tile([s for s in strip if s], 8, os.path.join(out, 'motion_%02d.jpg' % n), pad=4)

    loud = loudness(src)
    jumps = []
    voiced = sorted(v for v in loud if v > -35)
    voice = voiced[len(voiced) // 2] if voiced else -20.0      # the typical speaking level
    for i in range(3, len(loud)):
        # a cue sound climbs fast and lands clearly above the voice; speech onsets climb but stay at voice level
        if loud[i] >= voice + 5 and loud[i] - min(loud[i - 3:i]) >= 8 and all(abs(i / 10 - j) > 0.6 for j in jumps):
            jumps.append(round(i / 10, 1))
    words = None if '--no-words' in a else words_of(src)
    shots = [round(b - a2, 2) for a2, b in zip([0.0] + cuts, cuts + [dur])]
    rate = round(len(words) / max(0.1, (words[-1][2] - words[0][1])), 2) if words and len(words) > 1 else None
    pauses = [round(words[i + 1][1] - words[i][2], 2) for i in range(len(words) - 1)] if words else []
    summary = {
        'kind': 'video', 'file': src, 'length': round(dur, 2), 'size': [W, H], 'fps': round(fps, 3),
        'cuts': cuts, 'shot_lengths': shots, 'typical_shot': round(float(np.median(shots)), 2) if shots else None,
        'cuts_per_10s': round(len(cuts) / max(dur, 0.1) * 10, 2),
        'motion_moments': moments[:8], 'loudness_every_0.1s': loud, 'sound_jumps': jumps[:30],
        'words': words, 'words_per_second': rate,
        'long_pauses': sum(1 for p in pauses if p > 0.5), 'sampled_every': round(step, 2), 'sheets': math.ceil(len(frames) / 12),
    }
    json.dump(summary, open(os.path.join(out, 'study.json'), 'w'), indent=1)
    print('study: %s' % out)
    print('  %.1fs, %dx%d at %.0f fps. %d cuts (typical shot %.1fs, %.1f cuts per 10 s).'
          % (dur, W, H, fps, len(cuts), summary['typical_shot'] or dur, summary['cuts_per_10s']))
    print('  %s. %d sound jumps (check each against its frame: a pop on a word, a whoosh on a cut, music).'
          % ('%.1f words a second, %d pauses over half a second' % (rate, summary['long_pauses']) if rate else 'no speech found', len(jumps)))
    print('  Read: %d sheets, cuts.jpg, %d motion strips (motion_01 is the opening).' % (summary['sheets'], min(len(moments), 8)))


if __name__ == '__main__':
    main()
