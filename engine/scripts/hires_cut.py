#!/usr/bin/env python3
"""Full-resolution cut, so punch-ins and zooms stay sharp.

    python3 scripts/hires_cut.py <name>

The 1080x1920 cut (public/host/<name>-cut.mp4) is the timeline: captions, cutouts, audio and
every check come from it. This writes public/host/<name>-cut-hi.mp4 beside it: the same keep
segments, taken from the ORIGINAL recording through the same unmirror and reframe chain at
2160x3840, with the audio copied from the 1080 cut so both files run to the same sample. The
renderer draws the host from the hi file when it exists and scales it down, so a 1.4x opener
or a Hype zoom samples real pixels instead of stretching 1080p.

Skipped, with no file left behind, when the original recording cannot be found (an unmounted
drive) or has fewer than 1.5x the pixels of 1080p. The hi cut is checked against the 1080 cut
(frame count, duration, three sampled frames) and removed if it does not line up, so a wrong
file can never reach a render. Reused while the cut is unchanged.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HW, HH, FPS = 2160, 3840, 30
MIN_SOURCE_W = 1620          # below this the original has no detail to gain (1.5 x 1080)
MAX_SAMPLE_DIFF = 8.0        # mean luma difference allowed between a hi frame and the 1080 frame


def probe(path, entries):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_packets', '-show_entries', entries,
                          '-of', 'default=noprint_wrappers=1:nokey=1', path], capture_output=True, text=True).stdout
    return out.split()      # one value per line: the stream entries, then the format entries


def probe_kv(path, entries):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_packets', '-show_entries', entries,
                          '-of', 'default=noprint_wrappers=1', path], capture_output=True, text=True).stdout
    return dict(line.split('=', 1) for line in out.split() if '=' in line)


def cfr30(raw):
    """True when the recording is a plain 30 fps stream, so frame k of the normalized input IS
    frame k of the recording and the hi cut can pick frames by index in one pass."""
    kv = probe_kv(raw, 'stream=r_frame_rate,avg_frame_rate,nb_read_packets:format=duration')
    try:
        n, d = int(kv['nb_read_packets']), float(kv['duration'])
    except (KeyError, ValueError):
        return False
    return kv.get('r_frame_rate') == '%d/1' % FPS and kv.get('avg_frame_rate') == '%d/1' % FPS and abs(n - d * FPS) <= 2


def frame_diff(a, b, t):
    out = subprocess.run(['ffmpeg', '-v', 'error', '-ss', '%.3f' % t, '-i', a, '-ss', '%.3f' % t, '-i', b, '-filter_complex',
                          '[0]scale=270:480,format=gray[x];[1]scale=270:480,format=gray[y];[x][y]blend=all_mode=difference,signalstats,metadata=print:file=-',
                          '-frames:v', '1', '-f', 'null', '-'], capture_output=True, text=True).stdout
    for line in out.splitlines():
        if 'YAVG' in line:
            return float(line.split('=')[1])
    return 999.0


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    name = sys.argv[1]
    cut = os.path.join(ROOT, 'public', 'host', '%s-cut.mp4' % name)
    out = os.path.join(ROOT, 'public', 'host', '%s-cut-hi.mp4' % name)
    src_p = os.path.join(ROOT, 'qa', name, 'source.json')
    takes_p = os.path.join(ROOT, 'script', 'word-timings', '%s-takes.json' % name)

    def skip(why):
        if os.path.exists(out):
            os.remove(out)
        print('hires: skipped, %s (the render uses the 1080p cut)' % why)
        return 0

    if not (os.path.exists(cut) and os.path.exists(src_p) and os.path.exists(takes_p)):
        return skip('no cut, source record or takes file yet')
    rec = json.load(open(src_p))
    raw = rec.get('raw', '')
    if not os.path.exists(raw):
        return skip('the original recording is not reachable (%s)' % raw)
    w, h = rec.get('raw_size', [0, 0])
    if min(w, h) < MIN_SOURCE_W:
        return skip('the original is %dx%d, no extra detail over 1080p' % (w, h))
    newest_in = max(os.path.getmtime(cut), os.path.getmtime(takes_p))
    if os.path.exists(out) and os.path.getmtime(out) > newest_in:
        print('hires: reuse %s' % os.path.relpath(out, ROOT))
        return 0

    takes = json.load(open(takes_p))
    keep = [tuple(k) for k in takes['keep']]
    pics = [tuple(p) for p in takes.get('picture') or takes['keep']]   # J-cuts: the picture has its own spans
    tmp = out + '.part.mp4'
    if not cfr30(raw):
        # not a plain 30 fps recording (60 fps, variable rate): frame k of the normalized input is not
        # frame k of the recording, so build a full-resolution normalized twin with the very same
        # conversion and cut it with the very same keep times. Slower, exact.
        norm = out + '.norm.mp4'
        cmd = [sys.executable, os.path.join(HERE, 'normalize_source.py'), raw, norm, '--size', '%dx%d' % (HW, HH), '--no-record']
        cmd += ['--unmirror'] if rec.get('unmirrored') else []
        cmd += ['--reframe', str(rec['reframe'])] if float(rec.get('reframe') or 1.0) > 1.0 else []
        print('hires: %s is not plain 30 fps, normalizing it at %dx%d first (slow, exact)' % (os.path.basename(raw), HW, HH))
        if subprocess.run(cmd).returncode != 0:
            return skip('could not normalize the original at full resolution')
        sys.path.insert(0, HERE)
        import hostcut
        try:
            hostcut.render_cut(norm, keep, tmp, silences=[tuple(x) for x in takes['silences']], duration=float(takes['duration']),
                               forbidden_spans=[tuple(x) for x in takes.get('forbidden') or []] or None, min_join_silence=0.15, crf=18,
                               picture=pics if takes.get('picture') else None)
        except Exception as exc:   # the gate re-checks the same keep list against the same silences
            os.remove(norm)
            return skip('the full-resolution cut was refused: %s' % exc)
        os.remove(norm)
        return finish(cut, tmp, out, skip)
    chain = 'fps=%d' % FPS
    if rec.get('unmirrored'):
        chain += ',hflip'
    rf = float(rec.get('reframe') or 1.0)
    if rf > 1.0:
        chain += ',crop=trunc(iw/%f/2)*2:trunc(ih/%f/2)*2:(iw-ow)/2:ih-oh' % (rf, rf)
    chain += ',scale=%d:%d:force_original_aspect_ratio=increase:flags=lanczos,crop=%d:%d' % (HW, HH, HW, HH)
    # pick frames by index on the 30 fps grid, exactly the frames the 1080 cut holds: frame k
    # sits at k/30 s, and a segment [s, e) keeps ceil(30s) .. ceil(30e)-1
    import math
    n = len(keep)
    spans = [(math.ceil(s * FPS - 1e-6), math.ceil(e * FPS - 1e-6) - 1) for s, e in pics]
    expected = sum(b - a + 1 for a, b in spans)
    parts = ['[0:v]%s,split=%d%s' % (chain, n, ''.join('[s%d]' % i for i in range(n)))]
    for i, (a, b) in enumerate(spans):
        parts.append("[s%d]select='between(n\\,%d\\,%d)',setpts=N/%d/TB[v%d]" % (i, a, b, FPS, i))
    parts.append('%sconcat=n=%d:v=1:a=0[outv]' % (''.join('[v%d]' % i for i in range(n)), n))
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-i', raw, '-i', cut, '-filter_complex', ';'.join(parts),
           '-map', '[outv]', '-map', '1:a:0', '-c:v', 'libx264', '-crf', '18', '-preset', 'medium', '-pix_fmt', 'yuv420p',
           '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-c:a', 'copy',
           '-movflags', '+faststart', tmp]
    print('hires: cutting %d segments (%d frames) from %s at %dx%d' % (n, expected, os.path.basename(raw), HW, HH))
    r = subprocess.run(cmd)
    if r.returncode != 0:
        if os.path.exists(tmp):
            os.remove(tmp)
        return skip('ffmpeg could not build the full-resolution cut')

    return finish(cut, tmp, out, skip)


def finish(cut, tmp, out, skip):
    # the hi cut must be the 1080 cut, pixel for pixel, at twice the size
    fa, da = probe(cut, 'stream=nb_read_packets:format=duration')
    fb, db = probe(tmp, 'stream=nb_read_packets:format=duration')
    problems = []
    if fa != fb:
        problems.append('frame count %s vs %s' % (fa, fb))
    if abs(float(da) - float(db)) > 0.05:
        problems.append('duration %.3f vs %.3f' % (float(da), float(db)))
    dur = float(da)
    for t in (dur * 0.1, dur * 0.5, dur * 0.9):
        d = frame_diff(cut, tmp, t)
        if d > MAX_SAMPLE_DIFF:
            problems.append('frame at %.1fs differs (mean %.1f)' % (t, d))
    if problems:
        os.remove(tmp)
        return skip('the full-resolution cut did not line up with the 1080 cut: ' + '; '.join(problems))
    os.replace(tmp, out)
    print('hires: wrote %s (%s frames, %dx%d, %.1f MB)' % (os.path.relpath(out, ROOT), fb, HW, HH, os.path.getsize(out) / 1e6))
    return 0


if __name__ == '__main__':
    sys.exit(main())
