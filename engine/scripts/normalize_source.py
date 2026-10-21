#!/usr/bin/env python3
"""Step 0 — normalize a raw vertical recording into the engine's working source.

    python3 scripts/normalize_source.py <raw.MOV|mp4> inputs/<name>.mp4 [--unmirror]

--unmirror flips the picture horizontally. iPhone front-camera footage is saved mirrored
when Settings > Camera > Mirror Front Camera is on, so any text on screen reads backwards.

Output: 1080x1920, constant 30 fps, H.264 yuv420p bt709, ONE AAC track. Why here and
nowhere else: every later step (the copied transcriber and cutter, Remotion's
OffthreadVideo) then sees a canvas-sized, CFR, single-audio file. iPhone MOVs carry a
4-channel spatial-audio track and a slightly variable frame rate the frame math must
not inherit, and decoding 4K portrait per frame (twice during a swap) is 4x the cost.

VERTICAL ONLY (decided 2026-09-26): a landscape source is refused, not reframed.
The raw file is never modified. Source provenance lands in qa/<name>/source.json.
"""
import hashlib
import json
import os
import subprocess
import sys

W, H, FPS = 1080, 1920, 30


def probe(path):
    p = subprocess.run(['ffprobe', '-v', 'error', '-print_format', 'json', '-show_streams',
                        '-show_format', path], capture_output=True, text=True, check=True)
    return json.loads(p.stdout)


def display_size(stream):
    """Width/height after autorotation (ffmpeg rotates on decode by default)."""
    w, h = int(stream['width']), int(stream['height'])
    rot = 0
    for sd in stream.get('side_data_list', []) or []:
        if 'rotation' in sd:
            rot = int(float(sd['rotation']))
    rot = rot or int(float((stream.get('tags') or {}).get('rotate', 0)))
    return (h, w) if abs(rot) % 180 == 90 else (w, h)


def sha256(path, limit=64 * 1024 * 1024):
    """Hash of the first 64MB + size: identifies the take without reading 500MB twice."""
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        h.update(f.read(limit))
    h.update(str(os.path.getsize(path)).encode())
    return h.hexdigest()


def main():
    # --reframe Z: crop to 1/Z of the frame from the FULL-resolution source (no softening), keeping
    # the bottom edge and centering horizontally. Removes dead space above the subject (a backdrop
    # bar, the ceiling) before anything else sees the picture. Chris 2026-10-05: 1.16 for the black backdrop.
    reframe = 1.0
    if '--reframe' in sys.argv:
        reframe = float(sys.argv[sys.argv.index('--reframe') + 1])
    # --size WxH: another output size (scripts/hires_cut.py asks for 2160x3840); --no-record: leave qa/<name>/source.json alone
    OW, OH = W, H
    if '--size' in sys.argv:
        OW, OH = (int(x) for x in sys.argv[sys.argv.index('--size') + 1].lower().split('x'))
    flags = ('--reframe', '--size')
    skip = {i for i, a in enumerate(sys.argv) if a in flags} | {i + 1 for i, a in enumerate(sys.argv) if a in flags}
    args = [a for i, a in enumerate(sys.argv) if i and i not in skip and a not in ('--unmirror', '--no-record')]
    unmirror = '--unmirror' in sys.argv
    if len(args) != 2:
        sys.exit('usage: normalize_source.py <raw> inputs/<name>.mp4 [--unmirror] [--reframe 1.16] [--size WxH] [--no-record]')
    raw, out = args
    raw = os.path.realpath(os.path.expanduser(raw))
    info = probe(raw)
    vids = [s for s in info['streams'] if s.get('codec_type') == 'video']
    auds = [s for s in info['streams'] if s.get('codec_type') == 'audio' and s.get('codec_name') != 'apac']
    if not vids:
        sys.exit('normalize: no video stream in %s' % raw)
    if not auds:
        sys.exit('normalize: no usable audio stream in %s (the pipeline is driven by speech)' % raw)
    w, h = display_size(vids[0])
    if h <= w:
        sys.exit('normalize: %s is %dx%d (landscape). This engine is VERTICAL ONLY. '
                 'Use ../content-engine for landscape footage.' % (raw, w, h))
    a_idx = auds[0]['index']
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-i', raw,
           '-map', '0:v:0', '-map', '0:%d' % a_idx,
           '-vf', ('hflip,' if unmirror else '') + ('crop=trunc(iw/%f/2)*2:trunc(ih/%f/2)*2:(iw-ow)/2:ih-oh,' % (reframe, reframe) if reframe > 1.0 else '')
                  + 'scale=%d:%d:force_original_aspect_ratio=increase:flags=lanczos,crop=%d:%d' % (OW, OH, OW, OH),
           '-r', str(FPS), '-fps_mode', 'cfr',
           '-c:v', 'libx264', '-crf', '16', '-preset', 'medium', '-pix_fmt', 'yuv420p',
           '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709',
           '-c:a', 'aac', '-b:a', '192k', '-ac', '2', out]
    subprocess.run(cmd, check=True)
    name = os.path.splitext(os.path.basename(out))[0]
    qa = os.path.join('qa', name)
    os.makedirs(qa, exist_ok=True)
    rec = {'raw': raw, 'raw_sha256_head': sha256(raw), 'raw_size': [w, h],
           'raw_duration': float(info['format']['duration']), 'out': out,
           'out_size': [OW, OH], 'fps': FPS, 'audio_stream': a_idx, 'unmirrored': unmirror, 'reframe': reframe}
    if '--no-record' not in sys.argv:
        json.dump(rec, open(os.path.join(qa, 'source.json'), 'w'), indent=1)
    print('normalized %s (%dx%d) -> %s (%dx%d, %d fps CFR, 1 AAC track%s)' % (raw, w, h, out, OW, OH, FPS, ', UNMIRRORED' if unmirror else ''))


if __name__ == '__main__':
    main()
